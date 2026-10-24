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
# ---------------------------------------------------------------- usta: jedno otwarcie (szczyt) na sylabę
def peaks(m, lo=0.15, dip=0.6):
    """Szczyty otwarcia ust: maksima > lo; dwa sąsiednie liczą się osobno, jeśli między nimi szczęka przymyka się
    co najmniej do dip x mniejszego z nich (półotwarcia nie muszą zamykać się do zera)."""
    pk = [i for i in range(1, len(m) - 1) if m[i] > lo and m[i] >= m[i-1] and m[i] > m[i+1]]
    out = []
    for i in pk:
        if out and min(m[out[-1]:i + 1]) > dip*min(m[out[-1]], m[i]):
            if m[i] > m[out[-1]]: out[-1] = i
        else: out.append(i)
    return out
def mouth_check(curve, singer):
    pk = peaks(curve); pk_t = np.array(pk)/FPS
    lines = []; tot_s = tot_h = 0
    for L in E.AL['lines'] + E.AL.get('repeats', []):
        syl = []
        for w in L['words']:
            if singer in w['singers']: syl += (w.get('syl_choir') if singer == 'choir' and 'syl_choir' in w else w['syl'])
        if not syl: continue
        a, b = syl[0]['t_on'] - 0.05, syl[-1]['t_off'] + 0.05
        n_open = int(np.sum((pk_t >= a) & (pk_t <= b)))
        hit = sum(bool(np.any((pk_t >= s['t_on'] - 0.06) & (pk_t <= max(s['t_off'], s['t_on'] + 0.1)))) for s in syl)
        lines.append(dict(t0=round(L['t0'], 2), text=L['text'][:60], syllables=len(syl), openings=n_open, syllables_with_opening=hit))
        tot_s += len(syl); tot_h += hit
    return pk, lines, tot_s, tot_h
mouth = np.array([E.lead_mouth(t) for t in ts])
pk, lines, tot_s, tot_h = mouth_check(mouth, 'lead')
lv = np.array([E.vocal_level(t, 'lead') for t in ts]); act = lv > 0.15
R['lead_mouth'] = dict(total_syllables=tot_s, syllables_with_own_opening=tot_h, total_openings_in_lines=sum(l['openings'] for l in lines),
                       lines_exact=sum(l['syllables'] == l['openings'] for l in lines), lines_total=len(lines),
                       half_openings_pct=round(float(np.mean([mouth[i] < 0.7 for i in pk])*100), 1),
                       worst_lines=sorted(lines, key=lambda l: -abs(l['syllables'] - l['openings']))[:8],
                       corr_mouth_vs_vocal_envelope=round(float(np.corrcoef(mouth, lv)[0, 1]), 3),
                       mouth_open_when_vocal_silent_pct=round(float(np.mean(mouth[~act] > 0.2)*100), 2))
cm = np.array([E.choir_mouth(t, 0)/0.88 for t in ts])
cpk, clines, cs, ch_ = mouth_check(cm, 'choir')
R['choir_mouth'] = dict(lyric_syllables=cs, syllables_with_own_opening=ch_, lines=clines,
                        wordless_segments=len(E.AL['choir']['wordless']), hej=[h['t_on'] for h in E.AL['choir']['hej']])
# początki słów tam, gdzie gra stem wokalu (poziom w [t, t+150 ms] w górnych 20 dB stemu)
def stem_db(name):
    import soundfile as sf, librosa
    x, sr = sf.read(os.path.join(ROOT, 'build/wav', name), always_2d=True); x = x.mean(1)
    hop = int(0.01*sr); r = librosa.feature.rms(y=x, frame_length=4*hop, hop_length=hop)[0]
    return 20*np.log10(r + 1e-9)
for singer, stem in (('lead', '0_lead_vocals.wav'), ('choir', '1_backing_vocals.wav')):
    e = stem_db(stem); ok = n = 0; bad = []
    for L in E.AL['lines'] + E.AL.get('repeats', []):
        for w in L['words']:
            if singer not in w['singers'] or not w['syl']: continue
            t0 = (w.get('syl_choir') if singer == 'choir' and 'syl_choir' in w else w['syl'])[0]['t_on']
            seg = e[int(t0*100):int(t0*100) + 15]; n += 1
            if len(seg) and seg.max() > e.max() - 20: ok += 1
            else: bad.append((w['w'], round(t0, 2)))
    R.setdefault('word_starts_in_vocal', {})[singer] = dict(words=n, inside_pct=round(100*ok/max(n, 1), 1), outside=bad[:12])
R['alignment_crosscheck'] = json.load(open(os.path.join(ROOT, 'analysis/alignment_crosscheck.json')))
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
    c0, c1 = T.cam_at(s[0] + 0.02, s), T.cam_at(s[1] - 0.02, s)
    mv = abs(c1.x - c0.x) + abs(c1.y - c0.y) + abs(c1.d - c0.d) + 100*abs(c1.roll - c0.roll)
    if mv < 40: still.append(round(s[0], 2))
R['camera_static_shots'] = still
# ---------------------------------------------------------------- napisy: nie zasłaniają postaci (co 2 klatki)
worst = 0.0; worst_at = None; checked = 0; vis_min = 1.0; vis_at = None
for i in range(0, N, 2):
    t = i/FPS; s = T.shot_at(t)
    if s[2] != 'stage': continue
    cam = T.cam_at(t, s); acts = T.actors_at(t)
    for sg in T.SIGNS:
        if not sg.active(t) or sg.kind == 'marquee' or t < (sg.cut_in if sg.cut_in is not None else sg.t0 - 0.05): continue
        r = T.project_rect(cam, sg.rect(), sg.depth); checked += 1
        v = T.inter(r, T.FRAME)/max(T.area(r), 1)
        if v < vis_min: vis_min, vis_at = v, (round(t, 2), sg.key)
        for a in acts:
            if sg.kind in ('playboard', 'riser') and a.depth > sg.depth: continue     # lalka za panelem z napisem
            for rr in T.actor_rects(a):
                o = T.inter(r, T.project_rect(cam, rr, a.depth))/max(T.area(r), 1)
                if o > worst: worst, worst_at = o, (round(t, 2), sg.key, a.name)
R['signs'] = dict(sign_frames_checked=checked, max_overlap_fraction_with_character=round(worst, 4), at=worst_at,
                  min_visible_fraction=round(vis_min, 3), min_visible_at=vis_at,
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
