"""Dopasowanie tekstu do stemu wokalu prowadzącego odcinkami (pocketsphinx, dwa przebiegi).
Odcinki = okna między dłuższymi przerwami we frazach wokalu (a04 / lista fraz), każdy z przypisanymi wersami.
Wynik: build/ps_chunks.json"""
import json, sys, numpy as np
from ps_align import align, norm_word
from analysis_common import ROOT, os
S = json.load(open(os.path.join(ROOT, 'analysis/lyrics_struct.json')))
names = [s['name'] for s in S]
# (okno [s], lista (indeks części, indeksy wersów, czy wliczać chórek w nawiasach))
CHUNKS = [((2.5, 12.6), [(0, [0])]),
          ((13.4, 32.9), [(1, [0, 1, 2, 3, 4])]),
          ((32.9, 79.25), [(2, [0, 1, 2, 3]), (3, [0, 1, 2, 3]), (4, [0, 1, 2, 3, 4, 5])]),
          ((79.25, 99.5), [(5, [0, 1, 2, 3, 4])]),
          ((99.5, 102.5), [(6, [0])]),
          ((102.5, 128.2), [(7, [0, 1, 2, 3]), (8, [0, 1, 2, 3])]),
          ((128.2, 148.6), [(9, [0, 1, 2, 3, 4, 5])]),
          ((148.6, 165.5), [(10, [0, 1, 2, 3, 4])]),
          ((165.5, 187.6), [(11, [0, 1, 2, 3, 4, 5])]),
          ((187.6, 193.6), [(12, [0])])]
with_hej = len(sys.argv) > 1 and sys.argv[1] == 'hej'
allw = []
for (t0, t1), parts in CHUNKS:
    words, tags = [], []
    for si, lis in parts:
        for li in lis:
            l = S[si]['lines'][li]
            src = l['choir_words'] if names[si].startswith('Choir') else l['lead_words']
            for wi, w in enumerate(src):
                words.append(w['w']); tags.append((si, li, 'choir' if names[si].startswith('Choir') else 'lead', wi))
            if with_hej and l['choir'] and not names[si].startswith('Choir'):
                for wi, w in enumerate(l['choir_words']):
                    words.append(w['w']); tags.append((si, li, 'choir', wi))
    r = None
    for beam in (1e-60, 1e-80, 1e-100):
        r = align(words, t0, t1, beam=beam)
        if r is not None: break
    if r is None:
        print(f'FAILED chunk {t0}-{t1}'); continue
    ws = [x for x in r if x[0] not in ('<sil>', '<s>', '</s>')]
    assert len(ws) == len(words), (len(ws), len(words))
    for (w, a, b, ph), tg in zip(ws, tags):
        allw.append(dict(w=w, t0=round(a, 3), t1=round(b, 3), sec=tg[0], line=tg[1], part=tg[2], wi=tg[3],
                         ph=[[p, round(x, 3), round(y, 3)] for p, x, y in ph]))
    print(f'chunk {t0:6.1f}-{t1:6.1f}: {len(words)} words ok (beam {beam:g})')
json.dump(allw, open(os.path.join(ROOT, 'build/ps_chunks%s.json' % ('_hej' if with_hej else '')), 'w'), ensure_ascii=False)
prev = None
for o in allw:
    key = (o['sec'], o['line'], o['part'])
    if key != prev:
        print(f"\n{o['t0']:7.2f} [{names[o['sec']][:12]:12s}|{o['part'][0]}] ", end=''); prev = key
    print(f"{o['w']}", end=' ')
print()
