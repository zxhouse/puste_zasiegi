"""Montreal Forced Aligner (model polish_mfa v2.0.0a, GMM-HMM, słownik + g2p dla słów spoza słownika) - drugie, niezależne
akustycznie dopasowanie słów i fonemów. Segmenty = wersy (granice z dopasowania CTC rozszerzone o 0,6 s), audio = stem wokalu 16 kHz.
Wynik: build/asr/mfa_<stem>.json (słowa i fonemy z czasami bezwzględnymi)."""
import os, sys, json, subprocess, shutil, numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tools'); MFA = os.path.join(T, 'mamba/mfa/bin/mfa'); MD = os.path.join(T, 'models/mfa')
env = dict(os.environ, MAMBA_ROOT_PREFIX=os.path.join(T, 'mamba/root'), MFA_ROOT_DIR=os.path.join(ROOT, 'build/mfa_root'),
           PATH=os.path.join(T, 'mamba/mfa/bin') + ':' + os.environ['PATH'])
stem = sys.argv[1] if len(sys.argv) > 1 else 'lead'
src = json.load(open(os.path.join(ROOT, f'build/asr/ctc2_{stem}.json')))
W = src['words']
WORK = os.path.join(ROOT, f'build/mfa_{stem}'); shutil.rmtree(WORK, ignore_errors=True)
corp = os.path.join(WORK, 'corpus'); os.makedirs(corp)
wav = os.path.join(ROOT, 'build/wav', {'lead': '0_lead_vocals.wav', 'back': '1_backing_vocals.wav'}[stem])
x, sr = sf.read(wav, always_2d=True); x = librosa.resample(x.mean(1), orig_sr=sr, target_sr=16000)
# wersy (tylko słowa z pewnym dopasowaniem CTC w tym stemie)
lines = {}
for w in W:
    if w.get('present') and w['conf'] > -1.5: lines.setdefault((w['sec'], w['line'], w.get('occ', 0)), []).append(w)
segs = []
for k, ws in sorted(lines.items(), key=lambda kv: kv[1][0]['t0']):
    a = max(ws[0]['t0'] - 0.6, 0); b = ws[-1]['t1'] + 0.6
    name = f'l{k[0]:02d}_{k[1]}_{k[2]}'
    sf.write(os.path.join(corp, name + '.wav'), x[int(a*16000):int(b*16000)], 16000)
    open(os.path.join(corp, name + '.lab'), 'w').write(' '.join(w['sung'] for w in ws))
    segs.append(dict(name=name, a=a, b=b, words=[w['sung'] for w in ws]))
# słowa spoza słownika -> g2p
vocab = set(l.split('\t', 1)[0] for l in open(os.path.join(MD, 'polish_mfa.dict'), encoding='utf-8'))
oov = sorted(set(w for s in segs for w in s['words'] if w not in vocab))
open(os.path.join(WORK, 'oov.txt'), 'w').write('\n'.join(oov) + '\n')
subprocess.run([MFA, 'g2p', os.path.join(WORK, 'oov.txt'), os.path.join(MD, 'g2p/polish_mfa.zip'), os.path.join(WORK, 'oov.dict'), '--clean', '-q'], env=env, check=True)
d = os.path.join(WORK, 'full.dict')
with open(d, 'w', encoding='utf-8') as f:
    f.write(open(os.path.join(MD, 'polish_mfa.dict'), encoding='utf-8').read())
    for l in open(os.path.join(WORK, 'oov.dict'), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 2: f.write(f'{p[0]}\t0.99\t0.1\t1.0\t1.0\t{p[-1]}\n')
out = os.path.join(WORK, 'out')
r = subprocess.run([MFA, 'align', corp, d, os.path.join(MD, 'acoustic/polish_mfa.zip'), out, '--clean', '-q', '--output_format', 'json',
                    '--beam', '100', '--retry_beam', '400', '-j', '4'], env=env, capture_output=True, text=True)
print(r.stdout[-2000:], r.stderr[-3000:])
res = []
for s in segs:
    p = os.path.join(out, s['name'] + '.json')
    if not os.path.exists(p): res.append(dict(seg=s['name'], failed=True)); continue
    j = json.load(open(p)); tiers = j['tiers']
    words = [dict(w=e[2], t0=round(s['a'] + e[0], 3), t1=round(s['a'] + e[1], 3)) for e in tiers['words']['entries'] if e[2] not in ('', '<eps>')]
    phones = [dict(p=e[2], t0=round(s['a'] + e[0], 3), t1=round(s['a'] + e[1], 3)) for e in tiers['phones']['entries'] if e[2] not in ('', 'sil', '<eps>')]
    res.append(dict(seg=s['name'], words=words, phones=phones))
json.dump(dict(oov=oov, segments=res), open(os.path.join(ROOT, f'build/asr/mfa_{stem}.json'), 'w'), ensure_ascii=False, indent=0)
print('segmentów', len(segs), 'dopasowanych', sum(not r.get('failed') for r in res), 'OOV', len(oov))
