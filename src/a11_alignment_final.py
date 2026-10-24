"""Końcowe dopasowanie tekstu: sylaby z DP (a09) + poprawki + finał + chórki; metryki weryfikacji.
Wynik: analysis/alignment.json, analysis/alignment_check.txt"""
import json, numpy as np, scipy.ndimage as nd
from analysis_common import ROOT, os
S = json.load(open(os.path.join(ROOT, 'analysis/lyrics_struct.json')))
A = json.load(open(os.path.join(ROOT, 'build/syl_alignment.json')))
A0 = json.load(open(os.path.join(ROOT, 'build/syl_alignment_nopriors.json')))
P = json.load(open(os.path.join(ROOT, 'build/ps_word_priors.json')))
V = np.load(os.path.join(ROOT, 'build/vocal_feats.npz')); db = V['lead_db']; bdb = V['back_db']
LE = np.load(os.path.join(ROOT, 'build/syl_0_lead_vocals.npz'))['events']
BE = np.load(os.path.join(ROOT, 'build/syl_1_backing_vocals.npz'))['events']

# 1) scalone sylaby otwierające wers: czas = następna dopasowana sylaba - 0.14 s na każdą brakującą
for i, s in enumerate(A):
    if s['line_start'] and not s['matched']:
        j = i
        while j < len(A) and not A[j]['matched'] and (A[j]['sec'], A[j]['line']) == (s['sec'], s['line']): j += 1
        if j < len(A):
            for k in range(i, j):
                A[k]['t_on'] = round(A[j]['t_on'] - 0.14*(j - k), 3); A[k]['t_peak'] = round(A[k]['t_on'] + 0.06, 3)
                A[k]['t_off'] = round(A[k]['t_on'] + 0.13, 3)

# 2) finał (interpretacja spektrogramu): 'Pu-ste za-się-gi' rozciągnięte + 'hej', potem szybkie 'Pus-te za-się-gi' + 'HEJ!'
fin = []
def add(si, li, text, word, wi, k, t_on, t_off, part='lead', line_start=False):
    fin.append(dict(sec=si, line=li, wi=wi, k=k, text=text, word=word, line_start=line_start, word_start=(k == 0), optional=False,
                    spoken=False, t_on=t_on, t_peak=t_on + 0.08, t_off=t_off, matched=True, part=part))
oi = len(S) - 1; ol = len(S[oi]['lines']) - 1
for (txt, w, wi, k), (a, b) in zip([('Pu', 'Puste', 0, 0), ('ste', 'Puste', 0, 1), ('za', 'zasięgi', 1, 0), ('się', 'zasięgi', 1, 1), ('gi', 'zasięgi', 1, 2)],
                                   [(194.68, 195.10), (195.13, 195.52), (195.56, 196.15), (196.17, 197.6), (197.65, 201.40)]):
    add(oi, ol, txt, w, wi, k, a, b, line_start=(wi == 0 and k == 0))
finale_extra = [dict(text='hej', t_on=201.48, t_off=202.30), ]
reprise = list(zip(['Pus', 'te', 'za', 'się', 'gi'], [208.23, 208.53, 208.69, 208.94, 209.32], [208.50, 208.68, 208.92, 209.30, 209.70]))
reprise_hej = dict(text='HEJ', t_on=209.78, t_off=211.6)

# 3) słowa bez sylab (w, z): początek = początek następnego słowa - 0.06 s
lines = {}
for s in A: lines.setdefault((s['sec'], s['line']), []).append(s)
for s in fin: lines.setdefault((s['sec'], s['line']), []).append(s)
out_lines = []
for (si, li) in sorted(lines):
    syls = lines[(si, li)]; l = S[si]['lines'][li]
    choir_line = S[si]['name'].startswith('Choir')
    src = l['choir_words'] if choir_line else l['lead_words']
    words = []
    for wi, w in enumerate(src):
        ws = [s for s in syls if s['wi'] == wi]
        words.append(dict(w=w['w'], syl=[dict(text=s['text'], t_on=s['t_on'], t_peak=s['t_peak'], t_off=s['t_off'], matched=s['matched']) for s in ws]))
    for n, w in enumerate(words):
        if w['syl']: w['t0'] = w['syl'][0]['t_on']; w['t1'] = w['syl'][-1]['t_off']
    for n, w in enumerate(words):
        if not w['syl']:
            nxt = next((x for x in words[n+1:] if x['syl']), None)
            w['t0'] = round(nxt['t0'] - 0.06, 3) if nxt else words[n-1]['t1']; w['t1'] = nxt['t0'] if nxt else w['t0'] + 0.1
    out_lines.append(dict(sec=si, line=li, section=S[si]['name'], text=l['text'], spoken=l['spoken'], singer='choir' if choir_line else 'lead',
                          t0=min(w['t0'] for w in words), t1=max(w['t1'] for w in words), words=words))

# 4) chórki: zdarzenia stemu chórków przypisane do części; 'hej' = zdarzenie chórków po wersach 5-6 refrenu
choir = dict(events=[dict(t_on=round(float(e[0]), 3), t_peak=round(float(e[1]), 3), level=round(float(e[2]), 1)) for e in BE],
             hej=[], finale=finale_extra + [reprise_hej], reprise=[dict(text=a, t_on=b, t_off=c) for a, b, c in reprise])
for L in out_lines:
    l = S[L['sec']]['lines'][L['line']]
    if l['choir'] and L['singer'] == 'lead' and 'hej' in l['choir'].lower():
        # pierwsze zdarzenie chórków po końcu wersu (do 1.2 s)
        cand = BE[(BE[:, 0] > L['t1'] - 0.3) & (BE[:, 0] < L['t1'] + 1.2)]
        if len(cand): choir['hej'].append(dict(after_line=[L['sec'], L['line']], t_on=round(float(cand[0, 0]), 3)))

json.dump(dict(method='Zdarzenia sylabowe stemu wokalu + programowanie dynamiczne (kotwice z fraz, siatka 2-taktowa, priory słów z pocketsphinx en-us + g2p PL); finał wg spektrogramu',
               lines=out_lines, choir=choir), open(os.path.join(ROOT, 'analysis/alignment.json'), 'w'), ensure_ascii=False, indent=1)

# --- metryki
rep = []
allw = [w for L in out_lines for w in L['words'] if w['syl']]
def active_after(t, dur=0.15, thr=-20):
    a = int(t*100); return db[a:a+int(dur*100)].max() > thr
act = np.mean([active_after(w['t0']) for w in allw])
rep.append(f'Słów z sylabami: {len(allw)}; początek słowa w miejscu, gdzie wokal gra (max poziomu w [t, t+150 ms] > -20 dB): {act*100:.1f}%')
nos = [w for w in allw if not active_after(w['t0'])]
rep.append('  słowa bez wokalu na starcie: ' + ', '.join(f"{w['w']}@{w['t0']:.2f}" for w in nos[:20]))
# niezależna kontrola: DP BEZ priorów vs pocketsphinx (słowa)
d = []
for s in A0:
    key = f"{s['sec']}:{s['line']}:{s['wi']}"
    if s['word_start'] and key in P: d.append(s['t_on'] - P[key]['t'])
d = np.abs(np.array(d))
rep.append(f'Niezależnie: DP bez priorów vs pocketsphinx, początki słów (n={len(d)}): mediana {np.median(d)*1000:.0f} ms, <100 ms: {np.mean(d<0.1)*100:.0f}%, <200 ms: {np.mean(d<0.2)*100:.0f}%')
d2 = []
for s in A:
    key = f"{s['sec']}:{s['line']}:{s['wi']}"
    if s['word_start'] and key in P: d2.append(s['t_on'] - P[key]['t'])
d2 = np.abs(np.array(d2))
rep.append(f'Końcowe (z priorami) vs pocketsphinx: mediana {np.median(d2)*1000:.0f} ms, <100 ms: {np.mean(d2<0.1)*100:.0f}%')
# odległość onsetów sylab od wykrytych zdarzeń (tylko sylaby dopasowane = 0; scalone - raport liczby)
nm = sum(1 for s in A if not s['matched'])
rep.append(f'Sylab dopasowanych do zdarzenia wokalu: {len(A)-nm}/{len(A)}; scalonych (interpolowanych): {nm}')
open(os.path.join(ROOT, 'analysis/alignment_check.txt'), 'w').write('\n'.join(rep) + '\n')
print('\n'.join(rep))
for L in out_lines:
    print(f"{L['t0']:7.2f}-{L['t1']:7.2f} {L['section'][:12]:12s} {' '.join(w['w']+'@'+format(w['t0'],'.2f') for w in L['words'])[:150]}")
