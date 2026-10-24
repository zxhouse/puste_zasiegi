"""Niezależne narzędzia do sprawdzenia czasów słów z dopasowania CTC (Omnilingual, a23_ctc_skip.py):
  1. Montreal Forced Aligner (polish_mfa, GMM-HMM)               - build/asr/mfa_lead.json (a22_mfa.py)
  2. Whisper small (faster-whisper / CTranslate2), czasy słów     - rozpoznanie bez tekstu, język pl
  3. NVIDIA Parakeet TDT 0.6B v3 (sherpa-onnx), czasy tokenów      - rozpoznanie bez tekstu
  4. Silero VAD - fragmenty z głosem w stemie wokalu               - czy słowa leżą tam, gdzie jest głos
  5. Stare dopasowanie z v1/v2 (analysis/alignment.json)           - o ile się myliło
Dla każdego słowa z CTC szukamy tego samego słowa w wyniku narzędzia (podobieństwo pisowni) w ±1,5 s; różnica początków.
Wynik: analysis/alignment_crosscheck.json + analysis/plots/20_crosscheck.png"""
import os, sys, json, re, difflib, numpy as np, soundfile as sf, librosa
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'build/asr'); M = os.path.join(ROOT, 'tools/models')
x, sr = sf.read(os.path.join(ROOT, 'build/wav/0_lead_vocals.wav'), always_2d=True)
x16 = librosa.resample(x.mean(1), orig_sr=sr, target_sr=16000).astype(np.float32)
def norm(w): return re.sub(r'[^a-ząćęłńóśźż]', '', w.lower())
CT = json.load(open(os.path.join(A, 'ctc2_lead.json')))['words']
ref = [w for w in CT if w.get('present') and w['conf'] > -0.8 and len(norm(w['sung'])) >= 2]
OUT = {}

def compare(name, hyp):
    """hyp: lista (t0, słowo). Zwraca statystyki różnic początków dla dopasowanych słów."""
    dts = []; used = set()
    for w in ref:
        best = None
        for i, (t, h) in enumerate(hyp):
            if i in used or abs(t - w['t0']) > 1.5: continue
            r = difflib.SequenceMatcher(None, norm(w['sung']), norm(h)).ratio()
            if r >= 0.6 and (best is None or abs(t - w['t0']) < abs(best[1] - w['t0'])): best = (i, t)
        if best: used.add(best[0]); dts.append(best[1] - w['t0'])
    d = np.abs(np.array(dts)) if dts else np.array([np.nan])
    OUT[name] = dict(words_compared=len(dts), of=len(ref), median_abs_ms=round(float(np.median(d))*1000, 1),
                     mean_signed_ms=round(float(np.mean(dts))*1000, 1) if dts else None,
                     within_50ms_pct=round(float(np.mean(d < 0.05))*100, 1), within_100ms_pct=round(float(np.mean(d < 0.1))*100, 1),
                     within_200ms_pct=round(float(np.mean(d < 0.2))*100, 1), over_500ms=int(np.sum(d > 0.5)))
    print(name, OUT[name], flush=True)
    return dts

# 1. MFA
mf = json.load(open(os.path.join(A, 'mfa_lead.json')))
hyp_mfa = [(w['t0'], w['w']) for s in mf['segments'] if not s.get('failed') for w in s['words']]
d_mfa = compare('mfa', hyp_mfa)

# 2. Whisper small
from faster_whisper import WhisperModel
wm = WhisperModel(os.path.join(M, 'whisper-small-ct2'), device='cpu', compute_type='int8', cpu_threads=4)
segs, info = wm.transcribe(x16, language='pl', word_timestamps=True, vad_filter=False, beam_size=5, condition_on_previous_text=False)
hyp_wh = [(w.start, w.word) for s in segs for w in s.words]
json.dump([dict(t0=round(t, 3), w=h) for t, h in hyp_wh], open(os.path.join(A, 'whisper_small_lead.json'), 'w'), ensure_ascii=False)
d_wh = compare('whisper_small', hyp_wh)

# 3. Parakeet TDT v3 (okna 20 s z zakładką, tokeny BPE -> słowa po znaczniku początku słowa)
import sherpa_onnx
P = os.path.join(M, 'sherpa/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8')
rec = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=os.path.join(P, 'encoder.int8.onnx'), decoder=os.path.join(P, 'decoder.int8.onnx'),
        joiner=os.path.join(P, 'joiner.int8.onnx'), tokens=os.path.join(P, 'tokens.txt'), num_threads=4, model_type='nemo_transducer')
hyp_pk = []; WIN, HOP = 20.0, 16.0; t = 0.0; last_end = -1
while t < len(x16)/16000:
    seg = x16[int(t*16000):int((t + WIN)*16000)]
    st = rec.create_stream(); st.accept_waveform(16000, seg); rec.decode_stream(st)
    r = st.result; cur = None
    for tok, ts in zip(r.tokens, r.timestamps):
        T0 = t + ts
        if tok.startswith('▁') or tok.startswith(' ') or cur is None:
            if cur and cur[0] > last_end and (cur[0] < t + HOP + 2 or t + WIN >= len(x16)/16000): hyp_pk.append(tuple(cur))
            cur = [T0, tok.lstrip('▁ ')]
        else: cur[1] += tok
    if cur and cur[0] > last_end and (cur[0] < t + HOP + 2 or t + WIN >= len(x16)/16000): hyp_pk.append(tuple(cur))
    last_end = max([h[0] for h in hyp_pk] + [last_end]); t += HOP
json.dump([dict(t0=round(t, 3), w=h) for t, h in hyp_pk], open(os.path.join(A, 'parakeet_lead.json'), 'w'), ensure_ascii=False)
d_pk = compare('parakeet_v3', hyp_pk)

# 4. Silero VAD
from silero_vad import load_silero_vad, get_speech_timestamps
vad = load_silero_vad(onnx=True)
import torch
sp = get_speech_timestamps(torch.from_numpy(x16), vad, sampling_rate=16000, return_seconds=True, min_silence_duration_ms=120, speech_pad_ms=20)
json.dump(sp, open(os.path.join(A, 'silero_vad_lead.json'), 'w'))
inside = [any(s['start'] - 0.05 <= w['t0'] <= s['end'] for s in sp) for w in ref]
OUT['silero_vad'] = dict(speech_segments=len(sp), word_starts_inside_speech_pct=round(100*np.mean(inside), 1),
                         outside=[(w['w'], w['t0']) for w, i in zip(ref, inside) if not i][:20])
print('silero_vad', OUT['silero_vad'], flush=True)

# 5. stare dopasowanie (v1/v2)
old = json.load(open(os.path.join(ROOT, 'analysis/alignment.json')))
hyp_old = [(w['t0'], w['w']) for L in old['lines'] if L['singer'] == 'lead' for w in L['words']]
d_old = compare('old_v2_alignment', hyp_old)

json.dump(OUT, open(os.path.join(ROOT, 'analysis/alignment_crosscheck.json'), 'w'), ensure_ascii=False, indent=1)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 1, figsize=(10, 4.5))
bins = np.linspace(-0.6, 0.6, 61)
for d, n in ((d_mfa, 'MFA'), (d_wh, 'Whisper small'), (d_pk, 'Parakeet v3'), (d_old, 'stare (v2)')):
    ax.hist(np.clip(d, -0.6, 0.6), bins, histtype='step', lw=1.6, label=f'{n} (n={len(d)})')
ax.set_xlabel('początek słowa w narzędziu − początek z CTC [s]'); ax.set_ylabel('liczba słów'); ax.legend(); ax.grid(alpha=0.3)
ax.set_title('Zgodność początków słów: Omnilingual CTC vs inne narzędzia (wokal prowadzący)')
fig.tight_layout(); fig.savefig(os.path.join(ROOT, 'analysis/plots/20_crosscheck.png'), dpi=110)
