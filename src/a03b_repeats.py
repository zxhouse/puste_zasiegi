"""Szukanie powtórzeń: odcinki przekątnych w SSM (stały lag) o długości >= 6 taktów i wysokim podobieństwie."""
import numpy as np, json
from analysis_common import *
S = np.load(os.path.join(ROOT, 'build/ssm.npy'))   # już uśrednione po 4 taktach wzdłuż przekątnej
J = json.load(open(os.path.join(ROOT, 'analysis/ssm_bars.json'))); bars = np.array(J['bars'])
nb = S.shape[0]
# normalizacja: z-score poza przekątną
off = S[~np.eye(nb, dtype=bool)]
Z = (S - off.mean())/off.std()
found = []
for lag in range(8, nb):
    d = np.array([Z[i, i+lag] for i in range(nb-lag)])
    # odcinki gdzie d > 1.0 (wygładzone)
    m = np.convolve(d, np.ones(3)/3, 'same') > 0.9
    i = 0
    while i < len(m):
        if m[i]:
            j = i
            while j < len(m) and m[j]: j += 1
            if j - i >= 6: found.append((float(d[i:j].mean()), i, i+lag, j-i))
            i = j
        else: i += 1
found.sort(reverse=True)
print('top repeated segments (z, barA, barB, len) -> times')
for z, a, b, L in found[:30]:
    print(f'z={z:4.2f}  bars {a:3d}-{a+L+3:3d} ~ {b:3d}-{b+L+3:3d}   {bars[a]:6.1f}-{bars[min(a+L+3,nb)]:6.1f}s  ~  {bars[b]:6.1f}-{bars[min(b+L+3,nb)]:6.1f}s')
json.dump([dict(z=z, a=a, b=b, len=L) for z, a, b, L in found], open(os.path.join(ROOT, 'analysis/repeats.json'), 'w'))
