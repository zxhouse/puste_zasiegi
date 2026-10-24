"""Onsety stopy / werbla / hi-hatu ze stemu perkusji + siatka bitów (okres i przesunięcie dopasowane do stopy)
oraz siła akcentu na każdym bicie. Wynik: analysis/beats.json"""
import numpy as np, json, scipy.signal as sg
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from analysis_common import *

x, sr = load('2_drums')
HOP = 240; NFFT = 2048
f, t, Z = sg.stft(x, sr, nperseg=NFFT, noverlap=NFFT-HOP, boundary=None, padded=False)
M = np.abs(Z); fps = sr/HOP
tt = (np.arange(M.shape[1])*HOP + NFFT/2)/sr
def bmask(lo, hi): return (f >= lo) & (f < hi)
def flux(lo, hi, comp=1e3):
    b = M[bmask(lo, hi)]; L = np.log1p(comp*b)
    return np.maximum(np.diff(L, axis=1, prepend=L[:, :1]), 0).mean(axis=0)
def energy(lo, hi): return (M[bmask(lo, hi)]**2).sum(axis=0) + 1e-12

E_low, E_mid, E_hi, E_body = energy(30, 110), energy(1500, 5000), energy(7000, 18000), energy(160, 300)
F_all = flux(30, 18000)

def pick(o, thr_k=2.0, min_gap=0.06, win=0.6):
    w = int(win*fps) | 1
    med = sg.medfilt(o, w); mad = sg.medfilt(np.abs(o - med), w) + 1e-9
    thr = med + thr_k*mad*1.4826 + 0.03*np.percentile(o, 99.5)
    return sg.find_peaks(o, height=thr, distance=int(min_gap*fps))[0]

def rise(e, i, pre=(-10, -2), post=(0, 6)):
    a = e[max(i+pre[0], 0):max(i+pre[1], 1)].mean(); b = e[i+post[0]:min(i+post[1], len(e))].max()
    return 10*np.log10(b/a)

ons = pick(F_all, 2.0, 0.06)
feat = np.array([[rise(E_low, i), rise(E_mid, i), rise(E_hi, i), rise(E_body, i),
                  10*np.log10(E_low[i:i+6].max()), 10*np.log10(E_mid[i:i+6].max()), 10*np.log10(E_hi[i:i+6].max())] for i in ons])
# progi: stopa = mocny przyrost dołu i wysoki poziom dołu; werbel = mocny przyrost środka+ciała; hat = przyrost góry bez dołu
lowlvl, midlvl, hilvl = feat[:, 4], feat[:, 5], feat[:, 6]
# progi z rozkładu cech (stopa ~ -20 dB w paśmie 30-110 Hz, werbel/hat << -40 dB w tym paśmie)
is_kick = (feat[:, 0] > 12) & (lowlvl > -34)
is_snare = (feat[:, 1] > 8) & (feat[:, 3] > 8) & (midlvl > -42) & ((lowlvl < -38) | (midlvl > lowlvl - 8))
is_hat = (feat[:, 2] > 6) & (hilvl > -52) & ~is_kick & ~is_snare
def refine(i, e):
    a = max(i-5, 1); seg = np.log(e[a-1:i+3]); d = np.diff(seg)
    return tt[a - 1 + int(np.argmax(d))] + 0.5*HOP/sr
kick_t = np.array([refine(i, E_low) for i in ons[is_kick]]); kick_s = feat[is_kick, 4]
snare_t = np.array([refine(i, E_mid) for i in ons[is_snare]]); snare_s = feat[is_snare, 5]
hat_t = np.array([refine(i, E_hi) for i in ons[is_hat]]); hat_s = feat[is_hat, 6]
print('onsets', len(ons), 'kick', len(kick_t), 'snare', len(snare_t), 'hat', len(hat_t), ' both k+s', (is_kick & is_snare).sum())

# --- 1) globalny okres i przesunięcie dopasowane do stopy (statystyka kołowa + MNK)
def coh(ts, w, T):
    z = (w*np.exp(2j*np.pi*ts/T)).sum()/w.sum(); return np.abs(z), np.angle(z)
w = np.ones(len(kick_t))
Ts = np.linspace(0.36, 0.45, 9001)
R = np.array([coh(kick_t, w, T)[0] for T in Ts])
T = Ts[np.argmax(R)]; r, ang = coh(kick_t, w, T); phi = (ang*T/(2*np.pi)) % T
for it in range(4):
    n = np.round((kick_t - phi)/T); res = kick_t - (phi + n*T); ok = np.abs(res) < 0.08
    phi, T = np.linalg.lstsq(np.vstack([np.ones(ok.sum()), n[ok]]).T, kick_t[ok], rcond=None)[0]
phi = phi % T
n = np.round((kick_t - phi)/T); res = kick_t - (phi + n*T)
print(f'GLOBAL: T={T:.5f}s BPM={60/T:.3f} offset={phi:.4f}; kicks <35ms: {np.mean(np.abs(res)<0.035)*100:.1f}%  median|res| {np.median(np.abs(res))*1000:.1f} ms')

# --- 2) lokalna korekta fazy: tempo utworu pływa o ~±0.7%, więc przesunięcie liczone lokalnie
#        (ważona regresja liniowa reszt stopy i werbla w oknie ±WIN s, waga trójsześcienna)
WIN = 2.6
anc_t = np.concatenate([kick_t, snare_t]); anc_w = np.concatenate([np.ones(len(kick_t)), 0.7*np.ones(len(snare_t))])
# słabe kotwice w miejscach bez perkusji: onsety sumy instrumentów (bez wokali)
inst = sum(load(n)[0] for n in STEMS[3:])
_, _, Zi = sg.stft(inst, sr, nperseg=NFFT, noverlap=NFFT-HOP, boundary=None, padded=False)
Li = np.log1p(1e3*np.abs(Zi)); Fi = np.maximum(np.diff(Li, axis=1, prepend=Li[:, :1]), 0).mean(axis=0)
inst_on = tt[pick(Fi, 3.0, 0.1)]
drum_near = np.array([np.sum(np.abs(anc_t - t0) < WIN) for t0 in inst_on])
weak = inst_on[drum_near < 5]
print('weak (instrumental) anchors in drumless regions:', len(weak))
anc_t = np.concatenate([anc_t, weak]); anc_w = np.concatenate([anc_w, 0.35*np.ones(len(weak))])
o = np.argsort(anc_t); anc_t, anc_w = anc_t[o], anc_w[o]
anc_r = anc_t - (phi + np.round((anc_t - phi)/T)*T)
def local_offset(tq):
    d = np.abs(anc_t - tq); m = d < WIN
    if m.sum() < 5: return None
    ww = anc_w[m]*(1 - (d[m]/WIN)**3)**3
    # odporna regresja: 3 iteracje z odrzucaniem odstających (>30 ms od dopasowania)
    keep = np.ones(m.sum(), bool)
    for _ in range(3):
        A = np.vstack([np.ones(keep.sum()), anc_t[m][keep] - tq]).T*np.sqrt(ww[keep])[:, None]
        c = np.linalg.lstsq(A, anc_r[m][keep]*np.sqrt(ww[keep]), rcond=None)[0]
        pred = c[0] + c[1]*(anc_t[m] - tq)
        keep = np.abs(anc_r[m] - pred) < 0.03
        if keep.sum() < 4: break
    return c[0]
dur = len(x)/sr
grid = phi + T*np.arange(0, int((dur - phi)/T) + 1)
offs = np.array([np.nan if (o := local_offset(g)) is None else o for g in grid])
ok = ~np.isnan(offs)
# rozwinięcie fazy (dryf może przekroczyć ±T/2), potem interpolacja w lukach i ograniczenie tempa zmian
offs[ok] = np.unwrap(offs[ok], period=T)
offs = np.interp(grid, grid[ok], offs[ok])
for _ in range(500):     # zmiana przesunięcia między sąsiednimi bitami ≤ 8 ms (tempo ±2%) - wygładzanie tylko lokalnie
    d = np.diff(offs); bad = np.where(np.abs(d) > 0.008)[0]
    if len(bad) == 0: break
    sm = np.convolve(np.pad(offs, 2, mode='edge'), np.ones(5)/5, 'valid')
    m = np.zeros(len(offs), bool)
    for i in bad: m[max(i-2, 0):i+3] = True
    offs[m] = sm[m]
beats = grid + offs
beats = beats[(beats >= 0) & (beats < dur)]
def resid(ts):
    i = np.searchsorted(beats, ts); i = np.clip(i, 1, len(beats)-1)
    return np.where(np.abs(ts - beats[i-1]) < np.abs(ts - beats[i]), ts - beats[i-1], ts - beats[i])
rk, rsn = resid(kick_t), resid(snare_t)
ibi = np.diff(beats)
print(f'LOCAL: kicks <35ms: {np.mean(np.abs(rk)<0.035)*100:.1f}%  <20ms: {np.mean(np.abs(rk)<0.02)*100:.1f}%  median|res| {np.median(np.abs(rk))*1000:.1f} ms; snares <35ms {np.mean(np.abs(rsn)<0.035)*100:.1f}%')
print(f'local beat period range {ibi.min():.4f}..{ibi.max():.4f} s ({60/ibi.max():.1f}..{60/ibi.min():.1f} BPM)')
res, rs = rk, rsn
def near(ts, b, tol=0.045): return np.array([np.any(np.abs(ts - bi) < tol) for bi in b])
kick_on, snare_on, hat_on = near(kick_t, beats), near(snare_t, beats), near(hat_t, beats)
bi = np.arange(len(beats))
import librosa
harm = load('3_bass')[0] + load('5_keyboard')[0] + 0.5*load('10_brass')[0] + 0.5*load('4_guitar')[0]
C = librosa.feature.chroma_cqt(y=librosa.resample(harm, orig_sr=sr, target_sr=22050), sr=22050, hop_length=256)
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=22050, hop_length=256)
bc = np.array([C[:, (ct >= a) & (ct < b)].mean(axis=1) if ((ct >= a) & (ct < b)).any() else np.zeros(12)
               for a, b in zip(beats, np.append(beats[1:], beats[-1] + T))])
bc = bc/(np.linalg.norm(bc, axis=1, keepdims=True) + 1e-9)
hnov = np.r_[0, 1 - (bc[1:]*bc[:-1]).sum(axis=1)]           # zmiana akordu na danym bicie
bass_x = load('3_bass')[0]; benv = rms_env(bass_x, sr, 0.005, 0.02); bte = np.arange(len(benv))*0.005 + 0.01
bass_on = np.array([np.log((benv[(bte > b-0.02) & (bte < b+0.06)].max()+1e-6)/(benv[(bte > b-0.15) & (bte < b-0.03)].mean()+1e-6)) for b in beats])
scores = []
for p in range(4):
    sc_d = kick_on[(bi-p) % 4 == 0].sum()*2 + kick_on[(bi-p) % 4 == 2].sum() + snare_on[(bi-p) % 2 == 1].sum() - snare_on[(bi-p) % 4 == 0].sum()
    sc_h = hnov[(bi-p) % 4 == 0].sum() - hnov[(bi-p) % 4 == 2].sum()
    sc_b = np.clip(bass_on, 0, None)[(bi-p) % 4 == 0].sum() - np.clip(bass_on, 0, None)[(bi-p) % 4 == 2].sum()
    print(f'phase {p}: drums {sc_d}, harmonic change on 1 vs 3: {sc_h:.2f}, bass attacks 1 vs 3: {sc_b:.2f}')
    scores.append(sc_d + 20*sc_h)
bar_phase = int(np.argmax(scores)); print('bar phase ->', bar_phase)
beat_in_bar = (bi - bar_phase) % 4

# siła akcentu: szczyt obwiedni perkusji+perkusjonaliów w oknie bitu, dB -> 0..1
perc, _ = load('6_percussion')
env = rms_env(x + perc, sr, 0.005, 0.02); te = np.arange(len(env))*0.005 + 0.01
acc_db = np.array([20*np.log10(env[(te > b-0.03) & (te < b+0.06)].max() + 1e-6) for b in beats])
acc = np.clip((acc_db - np.percentile(acc_db, 5))/(np.percentile(acc_db, 99) - np.percentile(acc_db, 5)), 0, 1)

out = dict(period=float(T), bpm=float(60/T), offset=float(phi), bar_phase=bar_phase, local_window_s=WIN,
           local_period_min=float(ibi.min()), local_period_max=float(ibi.max()),
           beats=[dict(t=round(float(b), 4), beat_in_bar=int(k), accent=round(float(a), 3), kick=bool(ko), snare=bool(so), hat=bool(ho))
                  for b, k, a, ko, so, ho in zip(beats, beat_in_bar, acc, kick_on, snare_on, hat_on)],
           kick=[dict(t=round(float(a), 4), lvl=round(float(b), 1)) for a, b in zip(kick_t, kick_s)],
           snare=[dict(t=round(float(a), 4), lvl=round(float(b), 1)) for a, b in zip(snare_t, snare_s)],
           hat=[dict(t=round(float(a), 4), lvl=round(float(b), 1)) for a, b in zip(hat_t, hat_s)])
json.dump(out, open(os.path.join(ROOT, 'analysis/beats.json'), 'w'), indent=0)

fig, axs = plt.subplots(3, 1, figsize=(26, 9))
for ax, (a, b) in zip(axs, [(28, 48), (60, 80), (160, 180)]):
    m = (tt > a) & (tt < b)
    ax.plot(tt[m], 10*np.log10(E_low[m]), lw=0.5, label='low'); ax.plot(tt[m], 10*np.log10(E_mid[m]), lw=0.5, label='mid'); ax.plot(tt[m], 10*np.log10(E_hi[m]), lw=0.5, label='hi')
    for ts, c, y in [(kick_t, 'b', 20), (snare_t, 'orange', 25), (hat_t, 'g', 30)]:
        s = ts[(ts > a) & (ts < b)]; ax.plot(s, np.full(len(s), y), 'o', color=c, ms=4)
    bb = beats[(beats > a) & (beats < b)]; ax.vlines(bb, -60, 40, color='k', lw=0.4)
    bd = beats[(beats > a) & (beats < b) & (beat_in_bar == 0)]; ax.vlines(bd, -60, 40, color='r', lw=1.2)
    ax.set_ylim(-60, 40); ax.legend(loc='lower left')
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'analysis/plots/02_drums_zoom.png'), dpi=55)
plt.figure(figsize=(22, 4)); plt.plot(kick_t, res*1000, '.', label='kick'); plt.plot(snare_t, rs*1000, '.', label='snare'); plt.ylim(-100, 100); plt.grid(); plt.legend()
plt.ylabel('onset - siatka [ms]'); plt.savefig(os.path.join(ROOT, 'analysis/plots/02_grid_residuals.png'), dpi=60)
