"""Wspólne funkcje analizy audio (ładowanie stemów z build/wav)."""
import numpy as np, soundfile as sf, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, 'build', 'wav')
STEMS = ['0_lead_vocals','1_backing_vocals','2_drums','3_bass','4_guitar','5_keyboard',
         '6_percussion','7_strings','8_synth','9_other','10_brass','11_woodwinds']

def load(name, mono=True):
    x, sr = sf.read(os.path.join(WAV, name + '.wav'), dtype='float32')
    if mono and x.ndim == 2:
        x = x.mean(axis=1)
    return x, sr

def rms_env(x, sr, hop=0.01, win=0.03):
    h = int(sr*hop); w = int(sr*win)
    n = 1 + (len(x)-w)//h
    idx = np.arange(w)[None,:] + h*np.arange(n)[:,None]
    fr = x[idx]
    return np.sqrt((fr**2).mean(axis=1) + 1e-12)
