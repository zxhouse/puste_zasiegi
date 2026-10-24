"""Sprawdzenie liczbowe synchronizacji (z tych samych funkcji, z których renderowane są klatki, oraz z pikseli klatek).
Wynik: checks/verify_sync.json"""
import os, sys, json, math, subprocess
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video'))
import engine as E, timeline as T
ROOT = E.ROOT; OUT = os.path.join(ROOT, 'checks'); os.makedirs(OUT, exist_ok=True)
FPS = E.FPS; N = int(E.SONG_DUR*FPS)
ts = np.arange(N)/FPS
R = {}
# ---------------------------------------------------------------- usta Henia: jedno otwarcie na sylabę
mouth = np.array([E.lead_mouth(t) for t in ts])
def openings(m, hi=0.22, lo=0.12):
    """Liczba otwarć: przejścia powyżej hi po wcześniejszym zejściu poniżej lo (histereza)."""
    st = 'closed'; idx = []
    for i, v in enumerate(m):
        if st == 'closed' and v > hi: st = 'open'; idx.append(i)
        elif st == 'open' and v < lo: st = 'closed'
    return idx
op = openings(mouth)
lines = []
for L in E.AL['lines']:
    if L['singer'] != 'lead': continue
    syl = [s for w in L['words'] for s in w['syl']]
    # okno wersu: od klatki startu pierwszej sylaby do klatki przed startem pierwszej sylaby następnego wersu
    nxt_on = min([s['t_on'] for M in E.AL['lines'] if M['singer'] == 'lead' for w in M['words'] for s in w['syl'] if s['t_on'] > syl[-1]['t_on'] + 1e-3] + [1e9])
    a = int(math.ceil((syl[0]['t_on'] - 0.0125)*FPS - 1e-6))
    b = min(int(math.ceil((nxt_on - 0.0125)*FPS - 1e-6)) - 1, int(math.floor((max(s['t_off'] for s in syl) + 0.2)*FPS)))
    n_open = sum(a <= i <= b for i in op)
    # dla każdej sylaby: czy w jej oknie [t_on-0.05, t_off] jest początek otwarcia (z dokładnością do klatki)
    hit = 0
    for s in syl:
        i0, i1 = int((s['t_on'] - 0.06)*FPS), int(min(s['t_off'], s['t_on'] + 0.35)*FPS) + 1
        if any(i0 <= i <= i1 for i in op): hit += 1
    lines.append(dict(t0=round(L['t0'], 2), text=L['text'][:60], syllables=len(syl), openings=n_open, syllables_with_opening=hit))
tot_s = sum(l['syllables'] for l in lines); tot_o = sum(l['openings'] for l in lines); tot_h = sum(l['syllables_with_opening'] for l in lines)
R['lead_mouth'] = dict(total_syllables=tot_s, total_openings=tot_o, syllables_with_own_opening=tot_h, ratio_openings_per_syllable=round(tot_o/tot_s, 3),
                       lines_exact=sum(l['syllables'] == l['openings'] for l in lines), lines_total=len(lines),
                       worst_lines=sorted(lines, key=lambda l: -abs(l['syllables'] - l['openings']))[:8])
# usta vs obwiednia wokalu (korelacja na ramkach 10 ms -> klatki)
lv = np.array([E.vocal_level(t, 'lead') for t in ts])
act = lv > 0.15
R['lead_mouth']['corr_mouth_vs_vocal_envelope'] = round(float(np.corrcoef(mouth, lv)[0, 1]), 3)
R['lead_mouth']['mouth_open_when_vocal_silent_pct'] = round(float(np.mean(mouth[~act] > 0.2)*100), 2)
R['lead_mouth']['vocal_active_frames_with_mouth_open_pct'] = round(float(np.mean(mouth[act] > 0.12)*100), 2)
# chór: otwarcia vs zdarzenia sylabowe stemu chórków
cm = np.array([E.choir_mouth(t, 0) for t in ts]); co = openings(cm, 0.2, 0.1)
bev = E.BACK_EV[:, 0]
d = [min(abs(i/FPS - bev)) for i in co]
R['choir_mouth'] = dict(openings=len(co), backing_events=len(bev), median_dist_to_event_ms=round(float(np.median(d))*1000, 1),
                        pct_within_100ms=round(float(np.mean(np.array(d) < 0.1)*100), 1))
# ---------------------------------------------------------------- akcenty ruchu vs prawdziwe uderzenia
acc = np.array([E.kick(t, decay=0.14) + E.snare(t, decay=0.12) for t in ts])
pk = [i for i in range(1, N - 1) if acc[i] > 0.35 and acc[i] >= acc[i-1] and acc[i] > acc[i+1]]
hits = np.sort(np.concatenate([E.KICK, E.SNARE]))
dd = np.array([np.min(np.abs(hits - i/FPS)) for i in pk])
R['accents'] = dict(accent_peaks=len(pk), median_dist_to_drum_hit_ms=round(float(np.median(dd))*1000, 1), pct_within_1_frame=round(float(np.mean(dd < 1/FPS + 1e-6)*100), 1),
                    pct_within_2_frames=round(float(np.mean(dd < 2/FPS + 1e-6)*100), 1))
# błyski na werblu
fl = []
for t in ts:
    sc = T.shot_at(t)
    fl.append(T.lights_at(t, []).get('flash', 0.0) if sc[2] == 'stage' else 0.0)
fl = np.array(fl); fp = [i for i in range(1, N - 1) if fl[i] > 0.2 and fl[i] >= fl[i-1] and fl[i] > fl[i+1]]
hits2 = np.sort(np.concatenate([E.SNARE, np.array(T.HEJ + [T.FIN_HEJ, T.FINAL_HEJ, T.wt(T.CH1, 1, 5), T.wt(T.CH2, 1, 5), T.wt(T.V2, 4, 8)])]))
d2 = np.array([np.min(np.abs(hits2 - i/FPS)) for i in fp]) if fp else np.array([0.0])
R['flashes'] = dict(flash_peaks=len(fp), median_dist_to_snare_or_cue_ms=round(float(np.median(d2))*1000, 1), pct_within_2_frames=round(float(np.mean(d2 < 2/FPS + 1e-6)*100), 1))
# ---------------------------------------------------------------- cięcia: na początku wersu albo na 'raz' taktu
line_starts = sorted([L['t0'] for L in E.AL['lines']])
# początki zdań wewnątrz wersu mówionego (po '?', '.', '!' i pauzie) też są początkami fraz
for L in E.AL['lines']:
    toks = L['text'].split()
    if L['spoken']:
        for w, prev in zip(L['words'][1:], L['words'][:-1]):
            if w['t0'] - prev['t1'] > 0.25: line_starts.append(w['t0'])
line_starts = np.array(sorted(line_starts))
cuts = []
for s in T.SHOTS[1:]:
    c = s[0]
    if c >= E.SONG_DUR: continue
    dl = float(np.min(np.abs(line_starts - c))); db = float(np.min(np.abs(E.BARS - c)))
    cuts.append(dict(t=round(c, 3), to=s[2], dist_line_ms=round(dl*1000), dist_downbeat_ms=round(db*1000), ok=bool(min(dl, db) < 0.07 or s[2] == 'feed')))
R['cuts'] = dict(n=len(cuts), on_line_or_downbeat=sum(c['ok'] for c in cuts), list=cuts)
# ruch kamery w każdym ujęciu sceny
still = []
for s in T.SHOTS:
    if s[2] not in ('stage', 'under'): continue
    c0, c1 = s[3][0][1], s[3][-1][1]
    mv = abs(c1.x - c0.x) + abs(c1.y - c0.y) + abs(c1.d - c0.d) + 100*abs(c1.roll - c0.roll)
    if mv < 40: still.append(round(s[0], 2))
R['camera_static_shots'] = still
# ---------------------------------------------------------------- napisy: nie zasłaniają postaci (co 2 klatki)
worst = 0.0; worst_at = None; checked = 0
for i in range(0, N, 2):
    t = i/FPS; s = T.shot_at(t)
    if s[2] != 'stage': continue
    cam = T.cam_at(t, s); acts = T.actors_at(t)
    for sg in T.SIGNS:
        if not sg.active(t) or sg.kind == 'marquee': continue
        r = T.project_rect(cam, sg.rect(), sg.depth); checked += 1
        for a in acts:
            # tylko postaci przed napisem mogłyby być zasłonięte, gdy napis jest bliżej kamery
            if a.depth <= sg.depth and sg.kind not in ('playboard',): continue
            ar = T.project_rect(cam, T.actor_rect(a), a.depth)
            o = T.inter(r, ar)/max(T.area(r), 1)
            if o > worst: worst, worst_at = o, (round(t, 2), sg.key, a.name)
R['signs'] = dict(sign_frames_checked=checked, max_overlap_fraction_with_character_in_front=round(worst, 4), at=worst_at,
                  placement=[dict(line=list(k), kind=kd, visibility=float(v), overlap=float(o)) for k, kd, v, o in T.SIGN_REPORT])
# ---------------------------------------------------------------- chór: liczebność i brak nachodzenia w układzie grupowym
counts = []; overl = 0
for t in np.arange(46.0, 80.0, 0.5).tolist() + np.arange(115.0, 149.0, 0.5).tolist() + np.arange(167.0, 202.0, 0.5).tolist():
    acts = [a for a in T.actors_at(t) if a.name.startswith('Chór') and abs(a.y - T.CHOIR_Y) < 1]
    counts.append((round(t, 1), len(acts)))
    def body(a):
        ch = a.ch; s = a.scale*ch.scale; w = max(ch.torso_w[1] + 6, ch.head_w*1.15)
        return (a.x - w*s, a.y + (ch.head_y - ch.head_h - 30)*s, a.x + w*s, a.y)
    rs = sorted([body(a) for a in acts])
    for r1, r2 in zip(rs[:-1], rs[1:]):
        hx = min(r1[2], r2[2]) - max(r1[0], r2[0])
        if hx > 0: overl += 1
R['choir'] = dict(counts=counts, overlapping_pairs=overl)
json.dump(R, open(os.path.join(OUT, 'verify_sync.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: (v if k not in ('cuts', 'signs', 'choir') else {kk: vv for kk, vv in v.items() if kk not in ('list', 'placement', 'counts')}) for k, v in R.items()}, ensure_ascii=False, indent=1))
