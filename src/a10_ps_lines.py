"""Drugi przebieg pocketsphinx: każdy wers osobno, w oknie wyznaczonym przez DP (a09).
Akceptujemy tylko wyniki pełne (wszystkie słowa) i nie 'przyklejone' do brzegów okna.
Wynik: build/ps_word_priors.json  {klucz 'sec:line:wi': czas początku słowa}"""
import json, numpy as np
from ps_align import align
from analysis_common import ROOT, os
S = json.load(open(os.path.join(ROOT, 'analysis/lyrics_struct.json')))
A = json.load(open(os.path.join(ROOT, 'build/syl_alignment.json')))
lines = {}
for s in A:
    lines.setdefault((s['sec'], s['line']), []).append(s)
keys = sorted(lines)
priors = {}
# 1) wyniki odcinków z a07 (udane okna)
for w in json.load(open(os.path.join(ROOT, 'build/ps_chunks.json'))):
    if w['part'] == 'lead' or S[w['sec']]['name'].startswith('Choir'):
        priors[f"{w['sec']}:{w['line']}:{w['wi']}"] = dict(t=w['t0'], src='chunk')
# 2) wers po wersie
ok_n = 0
for n, k in enumerate(keys):
    l = S[k[0]]['lines'][k[1]]
    words = [w['w'] for w in (l['choir_words'] if S[k[0]]['name'].startswith('Choir') else l['lead_words'])]
    a = lines[k][0]['t_on']; b = lines[keys[n+1]][0]['t_on'] if n + 1 < len(keys) else lines[k][-1]['t_off'] + 0.5
    if b - a > 9: b = a + 9
    res = None
    for pa, pb in [(0.35, 0.0), (0.5, 0.15), (0.25, -0.1), (0.6, 0.3)]:
        r = align(words, a - pa, b + pb, beam=1e-80)
        if r is None: continue
        ws = [x for x in r if x[0] not in ('<sil>', '<s>', '</s>')]
        if len(ws) != len(words): continue
        if ws[0][1] - (a - pa) < 0.04 or (b + pb) - ws[-1][2] < 0.0: continue   # przyklejone do brzegu
        res = ws; break
    if res is None: continue
    ok_n += 1
    for wi, (w, t0, t1, ph) in enumerate(res):
        key = f'{k[0]}:{k[1]}:{wi}'
        if key in priors and priors[key]['src'] == 'chunk':
            priors[key]['t_line'] = t0
        else:
            priors[key] = dict(t=t0, src='line')
print('lines aligned individually:', ok_n, '/', len(keys), ' word priors:', len(priors))
# zgodność dwóch źródeł tam, gdzie są oba
d = [abs(v['t'] - v['t_line']) for v in priors.values() if 't_line' in v]
if d: print(f'chunk vs line agreement: median {np.median(d)*1000:.0f} ms, 90% {np.percentile(d, 90)*1000:.0f} ms, n={len(d)}')
json.dump(priors, open(os.path.join(ROOT, 'build/ps_word_priors.json'), 'w'))
