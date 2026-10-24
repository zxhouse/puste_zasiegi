"""Cechy wokalu prowadzącego i chórków: obwiednia RMS, pasmo wokalne, onsety, f0/dźwięczność (pyin). -> build/vocal_feats.npz"""
import numpy as np, librosa, scipy.signal as sg
from analysis_common import *
SR = 16000; HOPS = 0.01
out = {}
for name, key in [('0_lead_vocals', 'lead'), ('1_backing_vocals', 'back')]:
    x, sr = load(name); y = librosa.resample(x, orig_sr=sr, target_sr=SR)
    hop = int(SR*HOPS)
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=hop, center=True))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    band = (f > 150) & (f < 5000)
    e = np.sqrt((S[band]**2).mean(0))
    db = 20*np.log10(e + 1e-7)
    L = np.log1p(1e2*S[band]); fl = np.maximum(np.diff(L, axis=1, prepend=L[:, :1]), 0).mean(0)
    mf = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=S**2, sr=SR, n_mels=40)), n_mfcc=14)
    out[key + '_db'] = db.astype(np.float32); out[key + '_flux'] = fl.astype(np.float32); out[key + '_mfcc'] = mf.astype(np.float32)
    if key == 'lead':
        f0, vflag, vprob = librosa.pyin(y, fmin=65, fmax=500, sr=SR, frame_length=1024, hop_length=hop)
        out['lead_f0'] = np.nan_to_num(f0).astype(np.float32); out['lead_vprob'] = vprob.astype(np.float32)
    print(key, 'frames', len(db), 'p95 dB', np.percentile(db, 95), 'p50', np.percentile(db, 50))
np.savez(os.path.join(ROOT, 'build/vocal_feats.npz'), **out)
