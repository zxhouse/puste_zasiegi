import numpy as np, json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from analysis_common import ROOT, os
a, b = float(sys.argv[1]), float(sys.argv[2]); out = sys.argv[3]
D = np.load(os.path.join(ROOT, 'build/syl_0_lead_vocals.npz'))
E = D['events']; lm = D['lm']
i0, i1 = int(a*100), int(b*100)
fig, ax = plt.subplots(2, 1, figsize=(26, 8), sharex=True, gridspec_kw=dict(height_ratios=[2, 1]))
ax[0].imshow(lm[:, i0:i1], origin='lower', aspect='auto', extent=[a, b, 0, 40], cmap='magma', vmin=lm.max()-70)
t = np.arange(i0, i1)/100
ax[1].plot(t, D['vow'][i0:i1], lw=0.8, label='vow'); ax[1].plot(t, D['loud'][i0:i1], lw=0.6, label='loud'); ax[1].plot(t, D['hf'][i0:i1], lw=0.6, label='hf')
st = np.where(D['f0'][i0:i1] > 0, 12*np.log2(np.maximum(D['f0'][i0:i1], 1)/110), np.nan)
ax2 = ax[1].twinx(); ax2.plot(t, st, 'k.', ms=1.5)
m = (E[:, 0] > a) & (E[:, 0] < b)
for on, pk, lv, pr, hf in E[m]:
    ax[0].axvline(on, color='c', lw=0.8); ax[1].axvline(on, color='c', lw=0.8); ax[1].plot(pk, lv, 'r^')
if len(sys.argv) > 4:
    W = json.load(open(sys.argv[4]))
    for w in W:
        if a < w['t0'] < b:
            ax[0].axvline(w['t0'], color='lime', lw=1.2, ls='--'); ax[0].text(w['t0'], 37, w['w'], color='lime', fontsize=9, rotation=45)
ax[1].legend(loc='lower left'); ax[1].set_xticks(np.arange(np.ceil(a), b, 0.5)); ax[1].grid(alpha=0.3)
plt.tight_layout(); plt.savefig(out, dpi=55)
