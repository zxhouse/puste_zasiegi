"""Dopasowanie sylab tekstu do zdarzeń sylabowych wokalu (programowanie dynamiczne).
Koszty: pominięcie zdarzenia (proporcjonalne do jego siły), brak zdarzenia dla sylaby (scalenie),
cisza wewnątrz słowa/wersu, nienaturalnie krótki/długi odstęp, początek wersu bez pauzy przed nim.
Wynik: analysis/alignment.json (wersy -> słowa -> sylaby z czasami)."""
import numpy as np, json, scipy.ndimage as nd
from analysis_common import ROOT, os
S = json.load(open(os.path.join(ROOT, 'analysis/lyrics_struct.json')))
D = np.load(os.path.join(ROOT, 'build/syl_0_lead_vocals.npz'))
E = D['events']                                 # onset, peak, level, prominence, hf
V = np.load(os.path.join(ROOT, 'build/vocal_feats.npz')); db = V['lead_db']
act = nd.binary_closing(db > -20, np.ones(8)); act = nd.binary_opening(act, np.ones(6))
FIN = 193.6                                     # finał chóralny (po ostatniej mowie) dopasowywany osobno
E = E[E[:, 0] < FIN]
J = len(E); t = E[:, 0]
prom = E[:, 3]; strength = np.clip((prom - 2)/10, 0.15, 1.0)
# cisza (luka aktywności) między zdarzeniami
def silence_between(a, b):
    i0, i1 = int(a*100) + 5, int(b*100) - 2
    if i1 <= i0: return 0.0
    seg = ~act[i0:i1]
    if not seg.any(): return 0.0
    lab, n = nd.label(seg)
    return max((lab == k).sum() for k in range(1, n+1))/100
gap_before = np.array([silence_between(t[j-1], t[j]) if j > 0 else 9.0 for j in range(J)])

# sylaby tekstu (wokal prowadzący + wtrącenie chóru, które jest też w stemie prowadzącym)
syl = []
for si, sec in enumerate(S):
    for li, l in enumerate(sec['lines']):
        choir_line = sec['name'].startswith('Choir')
        if sec['name'] == 'Outro' and not l['spoken']: continue      # finał chóralny -> a11
        words = l['choir_words'] if choir_line else l['lead_words']
        first = True
        for wi, w in enumerate(words):
            for k, sy in enumerate(w['syl']):
                syl.append(dict(sec=si, line=li, wi=wi, k=k, text=sy, word=w['w'], line_start=first, word_start=(k == 0),
                                optional=choir_line, spoken=l['spoken']))
                first = False
I = len(syl)
print('syllables', I, 'events', J)
# Kotwice: (część, wers) -> początek frazy wokalu po pauzie. Przypisanie wynika z tabeli fraz (a04/a08):
# liczba zdarzeń sylabowych we frazie = suma sylab kolejnych wersów (np. 33.10-48.96 s: 58 zdarzeń = 49 sylab
# zwrotki 1b + 9 sylab 1. wersu przedrefrenu). Kotwica jest miękka: ±0.3 s.
ANCHORS = {(0, 0): 3.28, (1, 0): 14.38, (2, 0): 33.10, (3, 1): 49.22, (4, 0): 60.14, (5, 0): 79.41, (5, 1): 83.45,
           (6, 0): 99.74, (7, 0): 102.65, (9, 0): 128.44, (10, 0): 149.00, (10, 1): 151.14, (11, 0): 167.81, (12, 0): 188.70}
# Miękkie oczekiwania: kolejne wersy w bloku zaczynają się co 2 takty (zmierzone na wersach pewnych:
# refren 1 takty 36/38/40/42, refren 3: 102/104/106/108, zwrotka 2: 50/52/54/56, bridge 92/94/96/98).
B = json.load(open(os.path.join(ROOT, 'analysis/beats.json'))); beats = np.array([b['t'] for b in B['beats']])
def bar_shift(t0, nbars):
    x = np.interp(t0, beats, np.arange(len(beats)))          # ułamkowy indeks bitu
    return float(np.interp(x + 4*nbars, np.arange(len(beats)), beats))
EXPECT = {}
def block(sec, lines, ref, start_bar=0):
    for n, li in enumerate(lines): EXPECT[(sec, li)] = bar_shift(ref, start_bar + 2*n)
block(1, [0, 1, 2, 3], 14.38); block(2, [0, 1, 2, 3], 33.27); block(3, [0, 1, 2, 3], 33.27, 8); block(4, [0, 1, 2, 3], 60.14)
block(5, [1, 2, 3, 4], 83.45); block(7, [0, 1, 2, 3], 102.65); block(8, [0, 1, 2, 3], 102.65, 8); block(9, [0, 1, 2, 3], 128.44)
block(10, [1, 2, 3, 4], 151.14); block(11, [0, 1, 2, 3], 167.81)
for sec, ref in [(4, 60.14), (9, 128.44), (11, 167.81)]:      # wersy 5-6 refrenu (z refrenu 3: +13.60 s, +16.03 s)
    EXPECT[(sec, 4)] = ref + 13.60; EXPECT[(sec, 5)] = ref + 16.03
expect_of = {}
for i, s_ in enumerate(syl):
    if s_['line_start'] and (s_['sec'], s_['line']) in EXPECT: expect_of[i] = EXPECT[(s_['sec'], s_['line'])]
# Priory słów z pocketsphinx (a07 odcinki + a10 wersy) - miękkie, jeśli plik istnieje
prior_of = {}
pp = os.path.join(ROOT, 'build/ps_word_priors.json')
if os.path.exists(pp) and os.environ.get('NO_PRIORS') is None:
    P = json.load(open(pp))
    for i, s_ in enumerate(syl):
        key = f"{s_['sec']}:{s_['line']}:{s_['wi']}"
        if s_['word_start'] and key in P: prior_of[i] = P[key]['t']
print('word priors used:', len(prior_of))
anchor_of = {}
for i, s_ in enumerate(syl):
    if s_['line_start'] and (s_['sec'], s_['line']) in ANCHORS: anchor_of[i] = ANCHORS[(s_['sec'], s_['line'])]
# kotwice słów w mówionym intro: 3 frazy wokalu (3.28 / 6.78 / 9.89 s) = 'No i co tam ... kochani?' / 'Kolejny sukces?' / 'Zobaczmy...'
WORD_ANCHORS = {(0, 0, 9): 6.78, (0, 0, 11): 9.89}
for i, s_ in enumerate(syl):
    if s_['word_start'] and (s_['sec'], s_['line'], s_['wi']) in WORD_ANCHORS: anchor_of[i] = WORD_ANCHORS[(s_['sec'], s_['line'], s_['wi'])]

INF = 1e9
K = 6                       # maks. liczba pomijanych zdarzeń między kolejnymi sylabami
cost = np.full((I + 1, J + 1), INF); back = np.zeros((I + 1, J + 1, 2), int)
# stan (i, j): i sylab dopasowanych, ostatnie użyte zdarzenie j-1 (j=0: żadne)
cost[0, 0] = 0
skipc = 0.55*strength
cum_skip = np.r_[0, np.cumsum(skipc)]
def trans_cost(i, jp, j):
    """sylaba i dopasowana do zdarzenia j, poprzednie dopasowane zdarzenie jp (-1 brak)."""
    s = syl[i]; c = 0.0
    if i in anchor_of and abs(t[j] - anchor_of[i]) > 0.3: return 50.0 + abs(t[j] - anchor_of[i])
    g = gap_before[j] if jp == j - 1 else silence_between(t[jp], t[j]) if jp >= 0 else 9.0
    dt = t[j] - t[jp] if jp >= 0 else 9.0
    if i in prior_of:
        c += min(4.0, 1.2*max(0.0, abs(t[j] - prior_of[i]) - 0.12)/0.2)
    if s['line_start']:
        if g < 0.08: c += 0.2                         # nowy wers zwykle po oddechu
        if i in expect_of:
            d = abs(t[j] - expect_of[i]); c += 2.0*max(0.0, d - 0.55)/0.3
    else:
        if g > 0.25: c += (4.0 if not s['word_start'] else 0.6)*min(g, 2.0)   # cisza w środku słowa / wersu
        if dt < 0.07: c += 1.5
        if dt > 1.4: c += (dt - 1.4)*1.5
    return c
for i in range(I + 1):
    for j in range(J + 1):
        c0 = cost[i, j]
        if c0 >= INF: continue
        # (a) sylaba i bez własnego zdarzenia (scalona z poprzednią)
        if i < I:
            mc = 0.25 if syl[i]['optional'] else (1.3 if not syl[i]['spoken'] else 0.7)
            if i in anchor_of: mc = 50.0
            if c0 + mc < cost[i + 1, j]:
                cost[i + 1, j] = c0 + mc; back[i + 1, j] = (i, j)
        # (b) dopasowanie sylaby i do zdarzenia jn (pomijając zdarzenia j..jn-1)
        if i < I:
            for jn in range(j, min(J, j + K + 1)):
                c = c0 + (cum_skip[jn] - cum_skip[j]) + trans_cost(i, j - 1, jn)
                if c < cost[i + 1, jn + 1]:
                    cost[i + 1, jn + 1] = c; back[i + 1, jn + 1] = (i, j)
        # (c) końcowe pominięcia zdarzeń po ostatniej sylabie
        if i == I and j < J:
            c = c0 + skipc[j]
            if c < cost[I, j + 1]:
                cost[I, j + 1] = c; back[I, j + 1] = (I, j)
# odtworzenie ścieżki
i, j = I, J
match = [None]*I
while i > 0 or j > 0:
    pi, pj = back[i, j]
    if pi == i - 1 and pj != j:          # dopasowanie
        match[i - 1] = j - 1
    i, j = pi, pj
print('total cost', round(cost[I, J], 2), 'matched', sum(m is not None for m in match), 'merged', sum(m is None for m in match))

# czasy sylab: onset ze zdarzenia; scalone -> interpolacja (dzielimy poprzednią sylabę)
on = np.full(I, np.nan); pk = np.full(I, np.nan)
for i, m in enumerate(match):
    if m is not None: on[i] = E[m, 0]; pk[i] = E[m, 1]
idx = np.where(~np.isnan(on))[0]
for i in np.where(np.isnan(on))[0]:
    a = idx[idx < i]; b = idx[idx > i]
    if len(a) and len(b):
        ia, ib = a[-1], b[0]
        frac = (i - ia)/(ib - ia)
        on[i] = on[ia] + frac*min(on[ib] - on[ia], 0.25*(ib - ia)); pk[i] = on[i] + 0.06
    elif len(a): on[i] = on[a[-1]] + 0.15*(i - a[-1]); pk[i] = on[i] + 0.06
    else: on[i] = on[b[0]] - 0.15*(b[0] - i); pk[i] = on[i] + 0.06
# koniec sylaby: początek następnej albo koniec aktywności wokalu
off = np.r_[on[1:], on[-1] + 0.5]
for i in range(I):
    a = int(on[i]*100); b = int(off[i]*100)
    seg = act[a:b]
    k0 = max(int((pk[i] - on[i])*100), 1)
    if len(seg) > k0 and not seg[k0:].all():
        k = np.argmax(~seg[k0:]) + k0              # pierwsza cisza po szczycie samogłoski
        if k > 3: off[i] = on[i] + k/100
out = []
for i, s in enumerate(syl):
    s2 = dict(s); s2.update(t_on=round(float(on[i]), 3), t_peak=round(float(pk[i]), 3), t_off=round(float(off[i]), 3),
                            matched=match[i] is not None)
    out.append(s2)
json.dump(out, open(os.path.join(ROOT, 'build/syl_alignment.json'), 'w'), ensure_ascii=False)
prev = None
for s in out:
    key = (s['sec'], s['line'])
    if key != prev:
        print(f"\n{s['t_on']:7.2f} {S[s['sec']]['name'][:13]:13s}: ", end=''); prev = key
    print(('' if s['word_start'] else '-') + (' ' if s['word_start'] else '') + s['text'] + ('' if s['matched'] else '*'), end='')
print()
