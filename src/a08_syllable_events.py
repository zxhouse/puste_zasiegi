"""Detektor zdarzeń sylabowych w stemie wokalu: każda śpiewana sylaba = narastanie energii/zmiana barwy/zmiana nuty.
Wynik: build/syl_events_<stem>.npz (czasy onsetów, siła, czas szczytu samogłoski, poziom)."""
import numpy as np, librosa, scipy.ndimage as nd, scipy.signal as sg, sys
from analysis_common import *
SR = 16000; HOP = 160; FPS = 100

def features(name):
    x, sr = load(name); y = librosa.resample(x, orig_sr=sr, target_sr=SR)
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=HOP, center=True))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    mel = librosa.feature.melspectrogram(S=S**2, sr=SR, n_mels=40, fmin=80, fmax=7000)
    lm = librosa.power_to_db(mel + 1e-10)
    loud = 10*np.log10((S[(f > 150) & (f < 4000)]**2).mean(0) + 1e-10)        # głośność pasma wokalnego
    vow = 10*np.log10((S[(f > 250) & (f < 1500)]**2).mean(0) + 1e-10)         # pasmo formantów samogłosek
    hf = 10*np.log10((S[(f > 3000) & (f < 7500)]**2).mean(0) + 1e-10)         # spółgłoski szumowe (s, sz, ś, cz)
    mf = librosa.feature.mfcc(S=lm, n_mfcc=13)[1:]
    mfd = np.sqrt((np.diff(mf, axis=1, prepend=mf[:, :1])**2).sum(0))          # tempo zmian barwy
    f0, vflag, _ = librosa.pyin(y, fmin=65, fmax=520, sr=SR, frame_length=1024, hop_length=HOP)
    return dict(loud=loud, vow=vow, hf=hf, mfd=mfd, f0=np.nan_to_num(f0), voiced=vflag.astype(float), lm=lm)

def events(F, floor_db=None):
    loud = nd.gaussian_filter1d(F['loud'], 1.5); vow = nd.gaussian_filter1d(F['vow'], 1.5)
    if floor_db is None: floor_db = np.percentile(loud, 97) - 32
    active = loud > floor_db
    # 1) szczyty samogłosek: lokalne maksima pasma formantowego z wyraźną doliną przed (spółgłoska / przerwa)
    pk, prop = sg.find_peaks(vow, prominence=2.5, distance=7)
    pk = pk[active[pk]]
    # 2) zmiany nuty (legato bez doliny energii): skok f0 > 0.8 półtonu trwale
    st = np.where(F['f0'] > 0, 12*np.log2(np.maximum(F['f0'], 1)/110), np.nan)
    stf = nd.median_filter(np.nan_to_num(st, nan=-99), 9)
    jump = np.abs(stf[8:] - stf[:-8]); jump = np.r_[np.zeros(4), jump, np.zeros(4)]
    jump[(stf < -50)] = 0
    # 3) onset sylaby: przed każdym szczytem szukamy początku narastania (min głośności w 250 ms przed szczytem)
    ev = []
    prev = -100
    for p in pk:
        a = max(p - 25, prev + 2, 0)          # nie cofamy się za poprzedni szczyt
        prev = p
        seg = vow[a:p+1]
        o = a + int(np.argmin(seg))
        # początek narastania: pierwsza ramka po minimum, gdzie przyrost > 1/4 różnicy
        rise = vow[o:p+1]; thr = rise[0] + 0.25*(rise[-1] - rise[0])
        on = o + int(np.argmax(rise >= thr))
        ev.append((on/FPS, p/FPS, vow[p], vow[p] - vow[o], F['hf'][max(on-5, 0):on+3].max()))
    ev = np.array(ev)
    # scalanie duplikatów: dwa szczyty z tym samym (lub prawie tym samym) onsetem -> jedno zdarzenie (silniejsze)
    keep = []
    for e in ev[np.argsort(ev[:, 0])]:
        if keep and (e[0] - keep[-1][0] < 0.035):
            if e[3] > keep[-1][3]: keep[-1] = e
        else: keep.append(e)
    return np.array(keep), active

if __name__ == '__main__':
    import pickle
    for name in ['0_lead_vocals', '1_backing_vocals']:
        F = features(name)
        E, active = events(F)
        np.savez(os.path.join(ROOT, f'build/syl_{name}.npz'), events=E, active=active, **{k: v for k, v in F.items()})
        print(name, 'events', len(E))
