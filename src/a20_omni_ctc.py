"""Omnilingual ASR (Meta, CTC 1B, ONNX z sherpa-onnx): prawdopodobieństwa znaków co 20 ms dla stemu wokalu.
Okna 30 s z zakładką 6 s (model przyjmuje < 40 s), sklejane środkami zakładek.
Wynik: build/asr/omni_<stem>.npz  (logp: klatki x znaki polskiego alfabetu + spacja + blank, greedy: argmax po całym słowniku)
Użycie: python3 a20_omni_ctc.py [lead|back]"""
import os, sys, numpy as np, soundfile as sf, librosa, onnxruntime as ort
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, 'tools/models/sherpa/sherpa-onnx-omnilingual-asr-1600-languages-1B-ctc-v2-int8-2026-02-05')
stem = sys.argv[1] if len(sys.argv) > 1 else 'lead'
wav = os.path.join(ROOT, 'build/wav', {'lead': '0_lead_vocals.wav', 'back': '1_backing_vocals.wav', 'mix': 'song.wav'}[stem])
OUT = os.path.join(ROOT, 'build/asr'); os.makedirs(OUT, exist_ok=True)
toks = {}
for l in open(os.path.join(MD, 'tokens.txt'), encoding='utf-8'):
    l = l.rstrip('\n'); k, v = l.rsplit(' ', 1); toks[k] = int(v)
inv = {v: k for k, v in toks.items()}
CHARS = list("aąbcćdeęfghijklłmnńoóprsśtuvwxyzźżq") + [' ', "'"]
cols = [0] + [toks[c] for c in CHARS]            # 0 = blank

x, sr = sf.read(wav, always_2d=True); x = x.mean(1)
x = librosa.resample(x, orig_sr=sr, target_sr=16000).astype(np.float32)
sess = ort.InferenceSession(os.path.join(MD, 'model.int8.onnx'), providers=['CPUExecutionProvider'])
WIN, HOP = 30*16000, 24*16000
starts = list(range(0, max(len(x) - WIN, 0) + HOP, HOP))
FR = 0.02
nfr = int(np.ceil(len(x)/16000/FR)) + 2
logp = np.full((nfr, len(cols)), -1e4, np.float32); greedy = np.zeros(nfr, np.int32); filled = np.zeros(nfr, bool)
for si, s in enumerate(starts):
    seg = x[s:s + WIN]
    if len(seg) < 4000: break
    z = (seg - seg.mean())/np.sqrt(seg.var() + 1e-5)
    lg = sess.run(None, {'x': z[None, :]})[0][0]                  # (T, V)
    lg = lg - lg.max(1, keepdims=True); lsm = lg - np.log(np.exp(lg).sum(1, keepdims=True))
    T = lsm.shape[0]; f0 = int(round(s/16000/FR))
    # z każdego okna bierzemy środek; brzegi okien (3 s) tylko tam, gdzie nie ma sąsiada
    a = 0 if si == 0 else int(3.0/FR); b = T if s + WIN >= len(x) else T - int(3.0/FR)
    for i in range(a, b):
        j = f0 + i
        if j >= nfr: break
        logp[j] = lsm[i, cols]; greedy[j] = int(lsm[i].argmax()); filled[j] = True
    print(f'okno {si}: {s/16000:.1f}-{(s + len(seg))/16000:.1f} s, {T} klatek', flush=True)
np.savez_compressed(os.path.join(OUT, f'omni_{stem}.npz'), logp=logp, greedy=greedy, filled=filled, chars=np.array(['<b>'] + CHARS), fr=FR)
# transkrypcja zachłanna z czasami (do podglądu, co model słyszy)
out = []; prev = -1; t0 = None; word = ''
for j, g in enumerate(greedy):
    if g != prev and g != 0:
        ch = inv.get(int(g), '?')
        if ch == ' ':
            if word: out.append((round(t0, 2), word)); word = ''
        else:
            if not word: t0 = j*FR
            word += ch
    prev = g
if word: out.append((round(t0, 2), word))
with open(os.path.join(OUT, f'omni_{stem}_greedy.txt'), 'w') as f:
    for t, w in out: f.write(f'{t:7.2f} {w}\n')
print(len(out), 'słów rozpoznanych')
