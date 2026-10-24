"""Mapa części utworu: granice z dopasowania wersów, potwierdzone powtarzalnością (SSM taktów a03/a03b
i korelacją chromy wokalu a06), dociągnięte do najbliższej 'raz' taktu przed pierwszym dźwiękiem wokalu.
Wynik: analysis/structure.json"""
import json, numpy as np
from analysis_common import ROOT, os
B = json.load(open(os.path.join(ROOT, 'analysis/beats.json'))); AL = json.load(open(os.path.join(ROOT, 'analysis/alignment.json')))
beats = np.array([b['t'] for b in B['beats']]); bib = np.array([b['beat_in_bar'] for b in B['beats']]); bars = beats[bib == 0]
L = AL['lines']
def first(sec_name_idx): return [l for l in L if l['sec'] == sec_name_idx]
def bar_before(t):            # ostatnia 'raz' przed t (z tolerancją 1 bitu dla przedtaktów)
    i = np.searchsorted(bars, t + 0.05) - 1; return int(max(i, 0))
secs = [  # (etykieta, typ, indeks części w tekście lub None, grupa powtórzeń)
    ('Intro (mowa)', 'intro', 0, None), ('Zwrotka 1a', 'verse', 1, 'V'), ('Zwrotka 1b', 'verse', 2, 'V'), ('Przedrefren 1', 'prechorus', 3, 'P'),
    ('Refren 1', 'chorus', 4, 'C'), ('Zwrotka 2a', 'verse', 5, 'V'), ('Wtrącenie chóru', 'choir', 6, None), ('Zwrotka 2b', 'verse', 7, 'V'),
    ('Przedrefren 2', 'prechorus', 8, 'P'), ('Refren 2', 'chorus', 9, 'C'), ('Bridge', 'bridge', 10, None), ('Refren 3', 'chorus', 11, 'C'),
    ('Outro', 'outro', 12, None)]
out = []
for lab, typ, si, grp in secs:
    ls = [l for l in L if l['sec'] == si]
    t0 = min(l['t0'] for l in ls); t1 = max(l['t1'] for l in ls)
    b0 = bar_before(t0)
    out.append(dict(label=lab, type=typ, lyric_section=si, repeat_group=grp, vocal_t0=round(t0, 3), vocal_t1=round(t1, 3),
                    bar=b0, bar_t=round(float(bars[b0]), 3), lines=[[round(l['t0'], 3), round(l['t1'], 3), l['text']] for l in ls]))
# instrumentalne wstawki między częściami
inst = [dict(label='Intro instr.', t0=0.0, t1=out[0]['vocal_t0']), dict(label='Instr. przed bridge→refren 3', t0=out[10]['vocal_t1'], t1=out[11]['vocal_t0'])]
res = dict(beat_period=B['period'], bpm=B['bpm'], bar_count=int(len(bars)), duration=212.04,
           repetition_evidence=dict(ssm='blok zwrotka1b→przedrefren1→refren1 powtórzony jako zwrotka2b→przedrefren2→refren2 (lag ~41-42 takty, z=2.27/2.17)',
                                    vocal_chroma='przedrefren 1 (46.3 s) ~ 112.9 s (0.90); refren 1 (59.0 s) ~ 127.4 s (0.90-0.92)'),
           sections=out, instrumental=inst)
json.dump(res, open(os.path.join(ROOT, 'analysis/structure.json'), 'w'), ensure_ascii=False, indent=1)
for s in out: print(f"{s['label']:18s} bar {s['bar']:3d} ({s['bar_t']:7.2f}s)  wokal {s['vocal_t0']:7.2f}-{s['vocal_t1']:7.2f}")
