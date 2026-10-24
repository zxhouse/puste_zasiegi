"""Części utworu z powtarzalności: macierz samopodobieństwa taktów (progresja akordów instrumentów,
chroma wokalu, barwa MFCC) -> krzywa nowości (jądro szachownicowe) -> granice -> grupowanie segmentów.
Wynik: analysis/sections_ssm.json + wykres."""
import numpy as np, json, librosa, scipy.signal as sg
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from analysis_common import *
B = json.load(open(os.path.join(ROOT, 'analysis/beats.json')))
beats = np.array([b['t'] for b in B['beats']]); bib = np.array([b['beat_in_bar'] for b in B['beats']])
SR = 22050; HOP = 256
def rs(x, sr): return librosa.resample(x, orig_sr=sr, target_sr=SR)
x, sr = load('song'); song = rs(x, sr)
harm = rs(load('3_bass')[0] + load('5_keyboard')[0] + 0.5*load('10_brass')[0] + 0.5*load('4_guitar')[0] + 0.5*load('7_strings')[0], sr)
lead = rs(load('0_lead_vocals')[0], sr); back = rs(load('1_backing_vocals')[0], sr); drums = rs(load('2_drums')[0], sr)
Ch = librosa.feature.chroma_cqt(y=harm, sr=SR, hop_length=HOP)
Cv = librosa.feature.chroma_cqt(y=lead + back, sr=SR, hop_length=HOP)
Mf = librosa.feature.mfcc(y=song, sr=SR, hop_length=HOP, n_mfcc=20)[1:]
def env(y): return librosa.feature.rms(y=y, hop_length=HOP)[0]
n_ = min(Ch.shape[1], Cv.shape[1], Mf.shape[1]); Ch, Cv, Mf = Ch[:, :n_], Cv[:, :n_], Mf[:, :n_]
ft = librosa.frames_to_time(np.arange(n_), sr=SR, hop_length=HOP)
El, Eb, Ed = env(lead)[:n_], env(back)[:n_], env(drums)[:n_]
bars = beats[bib == 0]
bars = np.append(bars, bars[-1] + 4*B['period'])
def seg_mean(F, a, b):
    m = (ft >= a) & (ft < b); return F[:, m].mean(axis=1) if m.any() else np.zeros(F.shape[0])
feats_h, feats_v, feats_m, info = [], [], [], []
for a, b in zip(bars[:-1], bars[1:]):
    q = np.linspace(a, b, 5)
    h = np.concatenate([seg_mean(Ch, q[i], q[i+1]) for i in range(4)])       # progresja w obrębie taktu
    v = np.concatenate([seg_mean(Cv, q[i], q[i+1]) for i in range(4)])
    feats_h.append(h/(np.linalg.norm(h)+1e-9)); feats_v.append(v/(np.linalg.norm(v)+1e-9)); feats_m.append(seg_mean(Mf, a, b))
    m = (ft >= a) & (ft < b)
    info.append(dict(lead=float(20*np.log10(El[m].mean()+1e-6)), back=float(20*np.log10(Eb[m].mean()+1e-6)), drums=float(20*np.log10(Ed[m].mean()+1e-6))))
H = np.array(feats_h); V = np.array(feats_v); Mm = np.array(feats_m)
Mm = (Mm - Mm.mean(0))/(Mm.std(0)+1e-9); Mm /= np.linalg.norm(Mm, axis=1, keepdims=True)
Sh, Sv, Sm = H@H.T, V@V.T, Mm@Mm.T
S = 0.45*Sh + 0.35*Sv + 0.2*(Sm+1)/2
nb = len(H)
# wzmocnienie ścieżek: średnia po przekątnej (4 takty)
L = 4
Sp = np.zeros_like(S)
for i in range(nb):
    for j in range(nb):
        k = [S[i+d, j+d] for d in range(L) if i+d < nb and j+d < nb]
        Sp[i, j] = np.mean(k)
# krzywa nowości (jądro szachownicowe 2x4 takty, gaussowskie)
K = 4
g = np.exp(-0.5*(np.linspace(-1.5, 1.5, 2*K))**2); G = np.outer(g, g)
sgn = np.sign(np.outer(np.r_[-np.ones(K), np.ones(K)], np.r_[-np.ones(K), np.ones(K)]))
ker = G*sgn
Spad = np.pad(S, K, mode='edge')
nov = np.array([(Spad[i:i+2*K, i:i+2*K]*ker).sum() for i in range(nb)])
nov = np.maximum(nov, 0)
# dodatkowo: zmiany obecności wokalu/chórków/perkusji
lv = np.array([d['lead'] for d in info]); bv = np.array([d['back'] for d in info]); dv = np.array([d['drums'] for d in info])
act = np.c_[lv > -40, bv > -40, dv > -40].astype(float)
actchg = np.r_[0, np.abs(np.diff(act, axis=0)).sum(1)]
score = nov/nov.max() + 0.35*actchg
pk, _ = sg.find_peaks(score, distance=3, height=0.25)
print('bar count', nb)
print('candidate boundaries (bar idx: time, score):')
for p in pk: print(f'  bar {p:3d}  t={bars[p]:7.2f}s  score={score[p]:.2f}  lead={lv[p]:.0f} back={bv[p]:.0f} drums={dv[p]:.0f}')
np.save(os.path.join(ROOT, 'build/ssm.npy'), Sp)
json.dump(dict(bars=bars.tolist(), novelty=score.tolist(), peaks=pk.tolist(), info=info), open(os.path.join(ROOT, 'analysis/ssm_bars.json'), 'w'))
fig, ax = plt.subplots(1, 2, figsize=(22, 10))
ax[0].imshow(Sp, origin='lower', cmap='magma', extent=[0, nb, 0, nb]); ax[0].set_title('SSM taktów (wzmocnione po przekątnej)')
for p in pk: ax[0].axvline(p, color='c', lw=0.6); ax[0].axhline(p, color='c', lw=0.6)
ax[0].set_xticks(range(0, nb, 4)); ax[0].set_yticks(range(0, nb, 4)); ax[0].tick_params(labelsize=6)
ax[1].plot(score); ax[1].plot(pk, score[pk], 'ro'); ax[1].set_xticks(range(0, nb, 4)); ax[1].grid(alpha=0.3)
ax[1].plot(act + np.array([1.2, 1.4, 1.6]), lw=0.8)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'analysis/plots/03_ssm.png'), dpi=70)
