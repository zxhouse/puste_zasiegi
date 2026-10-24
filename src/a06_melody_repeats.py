"""Niezależne sprawdzenie położenia powtarzalnych części: chroma (CENS) wokalu prowadzącego + chórków
wybranego fragmentu przesuwana po całym utworze (korelacja); odporna na błędy oktawowe f0."""
import numpy as np, sys, librosa, scipy.signal as sg
from analysis_common import *
cache = os.path.join(ROOT, 'build/vocal_cens.npy')
if not os.path.exists(cache):
    x, sr = load('0_lead_vocals'); y = librosa.resample(x, orig_sr=sr, target_sr=22050)
    C = librosa.feature.chroma_cens(y=y, sr=22050, hop_length=2205, win_len_smooth=5)   # 10 fps
    np.save(cache, C)
C = np.load(cache)
def scan(a, b):
    q = C[:, int(a*10):int(b*10)]; n = q.shape[1]
    r = np.array([(q*C[:, s:s+n]).sum()/n for s in range(C.shape[1]-n)])
    return r
args = sys.argv[1:]
for i in range(0, len(args), 3):
    name, a, b = args[i], float(args[i+1]), float(args[i+2])
    r = scan(a, b)
    pk, _ = sg.find_peaks(r, distance=40)
    top = pk[np.argsort(r[pk])[::-1][:6]]
    print(f'{name:14s} {a:6.1f}-{b:6.1f}s:', ', '.join(f'{t/10:.1f}s ({r[t]:.2f})' for t in sorted(top)))
