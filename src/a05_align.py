"""Dopasowanie tekstu do nagrania (forced alignment) bez modeli ASR:
1) synteza mowy z tekstu (espeak-ng + mbrola pl1) -> znane czasy fonemów,
2) DTW między MFCC syntezy a MFCC stemu wokalu (tylko ramki aktywne, cisze usunięte z obu stron),
3) mapowanie granic fonemów/słów na czas nagrania,
4) korekta początków słów do najbliższego onsetu wokalu (±90 ms).
Wynik: analysis/alignment.json"""
import numpy as np, json, subprocess, os, tempfile, librosa, soundfile as sf, scipy.ndimage as nd
from analysis_common import ROOT
import lyrics as LY
TMP = os.path.join(ROOT, 'build', 'tts'); os.makedirs(TMP, exist_ok=True)
VOW = lambda p: p[0] in 'aeiouIE'
SR = 16000; HOP = 160

def pho_word(word):
    spoken = LY.SPECIAL.get(word.lower(), (word,))[0]
    out = subprocess.run(['espeak-ng', '-v', 'mb-pl1', '--pho', '-q', spoken], capture_output=True, text=True).stdout
    ph = []
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 2 and p[0] != '_': ph.append([p[0], int(p[1]), ' '.join(p[2:])])
    # słowa bez samogłoski w pisowni (w, z): espeak dodaje 'I' - usuwamy (w mowie doklejają się do następnego słowa)
    if not any(c in LY.V for c in word): ph = [q for q in ph if not VOW(q[0])]
    return ph

S = json.load(open(os.path.join(ROOT, 'analysis/lyrics_struct.json')))
items = []    # (sec_idx, line_idx, words)
for si, sec in enumerate(S):
    for li, l in enumerate(sec['lines']):
        if l['lead_words']: items.append((si, li, l))

# --- synteza wersami: łączymy fonemy słów w jeden plik .pho na wers
tts_feats, labels = [], []      # labels: per ramka (item, word, phon) albo -1 dla ciszy
phon_table = []                 # (item, word, phon_idx, name, t0, t1) w czasie syntezy danego wersu
for k, (si, li, l) in enumerate(items):
    lines = ['_ 120']; t = 0.12; wb = []
    for wi, w in enumerate(l['lead_words']):
        ph = pho_word(w['w'])
        for pi, (p, d, pitch) in enumerate(ph):
            if l['spoken'] is False and VOW(p): d = int(d*1.6)          # śpiew: dłuższe samogłoski
            lines.append(f'{p} {d} {pitch}'.strip())
            phon_table.append((k, wi, pi, p, t, t + d/1000)); t += d/1000
    lines.append('_ 120')
    pf = os.path.join(TMP, f'l{k:02d}.pho'); wf = os.path.join(TMP, f'l{k:02d}.wav')
    open(pf, 'w').write('\n'.join(lines) + '\n')
    subprocess.run(['mbrola', '-e', '/usr/share/mbrola/pl1/pl1', pf, wf], check=True, capture_output=True)
    y, sr = sf.read(wf); assert sr == SR
    S_ = np.abs(librosa.stft(y.astype(np.float32), n_fft=1024, hop_length=HOP, center=True))
    mf = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=S_**2, sr=SR, n_mels=40)), n_mfcc=14)
    ft = np.arange(mf.shape[1])*HOP/SR
    lab = np.full(len(ft), -1)
    for j, (kk, wi, pi, p, a, b) in enumerate(phon_table):
        if kk == k: lab[(ft >= a) & (ft < b)] = j
    keep = lab >= 0
    tts_feats.append(mf[:, keep]); labels.append(lab[keep])
T_mf = np.concatenate(tts_feats, axis=1); T_lab = np.concatenate(labels)
print('TTS frames', T_mf.shape[1], 'phonemes', len(phon_table))

V = np.load(os.path.join(ROOT, 'build/vocal_feats.npz'))
db = V['lead_db']; v_mf = V['lead_mfcc']; flux = V['lead_flux']
act = nd.binary_closing(db > -22, np.ones(5)); act = nd.binary_opening(act, np.ones(4))
v_idx = np.where(act)[0]
print('vocal active frames', len(v_idx), f'({len(v_idx)/100:.1f}s)')

def norm(F):
    F = F[1:13]
    d = librosa.feature.delta(F, width=5)
    G = np.vstack([F, 0.6*d])
    return (G - G.mean(1, keepdims=True))/(G.std(1, keepdims=True) + 1e-6)
A = norm(v_mf[:, v_idx]); B = norm(T_mf)
DS = 2
A2, B2 = A[:, ::DS], B[:, ::DS]
from scipy.spatial.distance import cdist
C = cdist(B2.T, A2.T, 'cosine').astype(np.float64)
print('cost', C.shape)
D, wp = librosa.sequence.dtw(C=C, step_sizes_sigma=np.array([[1, 1], [0, 1], [1, 0], [1, 2], [2, 1]]),
                              weights_add=np.array([0, 0.15, 0.15, 0.05, 0.05]), subseq=False)
wp = wp[::-1]
# mapa: indeks ramki syntezy -> czas wokalu (mediana dopasowanych ramek)
tts2voc = np.full(B2.shape[1], np.nan)
for bi in range(B2.shape[1]):
    m = wp[wp[:, 0] == bi, 1]
    tts2voc[bi] = np.median(m)
voc_time = v_idx[::DS][np.clip(np.round(tts2voc).astype(int), 0, len(v_idx[::DS]) - 1)]/100.0
lab2 = T_lab[::DS]
# czasy fonemów w nagraniu
ph_t = {}
for j in range(len(phon_table)):
    m = np.where(lab2 == j)[0]
    if len(m): ph_t[j] = (float(voc_time[m[0]]), float(voc_time[m[-1]] + DS/100))
# onsety wokalu do korekty
from scipy.signal import find_peaks
fl = nd.gaussian_filter1d(flux, 1.0)
on_pk, _ = find_peaks(fl, height=np.percentile(fl, 70), distance=6)
on_t = on_pk/100.0
def snap(t, tol=0.09):
    i = np.argmin(np.abs(on_t - t)); return float(on_t[i]) if abs(on_t[i] - t) < tol else t

result = []
for k, (si, li, l) in enumerate(items):
    words = []
    for wi, w in enumerate(l['lead_words']):
        js = [j for j, r in enumerate(phon_table) if r[0] == k and r[1] == wi and j in ph_t]
        if not js: continue
        t0 = ph_t[js[0]][0]; t1 = ph_t[js[-1]][1]
        vowels = [(phon_table[j][3], ph_t[j][0], ph_t[j][1]) for j in js if VOW(phon_table[j][3])]
        words.append(dict(w=w['w'], syl=w['syl'], t0=round(t0, 3), t0_snap=round(snap(t0), 3), t1=round(t1, 3),
                          vowels=[dict(p=p, t0=round(a, 3), t1=round(b, 3)) for p, a, b in vowels]))
    result.append(dict(sec=si, line=li, section=S[si]['name'], text=l['lead'], spoken=l['spoken'], words=words,
                       t0=words[0]['t0_snap'] if words else None, t1=words[-1]['t1'] if words else None))
json.dump(dict(method='espeak-ng+mbrola pl1 TTS, MFCC-DTW na ramkach aktywnych, korekta do onsetów ±90ms', lines=result),
          open(os.path.join(ROOT, 'analysis/alignment_raw.json'), 'w'), ensure_ascii=False, indent=1)
for r in result:
    print(f"{r['t0']:7.2f}-{r['t1']:7.2f}  {r['section'][:14]:14s} {r['text'][:70]}")
