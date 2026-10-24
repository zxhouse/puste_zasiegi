import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from analysis_common import *
fig, axs = plt.subplots(len(STEMS)+1, 1, figsize=(22, 18), sharex=True)
song, sr = load('song')
for ax, name in zip(axs, ['song'] + STEMS):
    x, sr = load(name)
    e = 20*np.log10(rms_env(x, sr, 0.05, 0.1))
    t = np.arange(len(e))*0.05
    ax.plot(t, e, lw=0.6); ax.set_ylim(-70, 0); ax.set_ylabel(name, rotation=0, ha='right', fontsize=8)
    ax.grid(alpha=0.3)
    act = (e > -45).mean()
    print(f'{name:18s} peak {e.max():6.1f} dB  active(>-45dB) {act*100:5.1f}%')
axs[-1].set_xticks(np.arange(0, 213, 5))
plt.tight_layout(); plt.savefig(os.path.join(ROOT,'analysis/plots/01_stems_overview.png'), dpi=60)
