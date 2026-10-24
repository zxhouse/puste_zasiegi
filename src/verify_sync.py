"""Sprawdzenie liczbowe synchronizacji (z tych samych funkcji, z których renderowane są klatki, oraz z pikseli klatek).
Wynik: checks/verify_sync.json"""
import os, sys, json, math, subprocess
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video'))
import engine as E, timeline as T, stage as S
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
# trzymane nuty: przez cały czas dźwięku w stemie (od szczytu sylaby do końca głosu, najdalej do następnej sylaby) usta otwarte
def held_check(S, DB, curve, k_amp=1.0):
    S = sorted(S, key=lambda d: d['on']); top = float(DB.max()); n = 0; frac = []; bad = []
    for k, s in enumerate(S):
        nxt = S[k+1]['on'] if k + 1 < len(S) else s['off'] + 4
        i0 = int(s['on']*100); pk = float(DB[i0:int(min(s.get('off_al', s['off']), nxt)*100) + 1].max())
        j = int(min(s.get('off_al', s['off']), nxt - 0.04)*100); lim = min(int((nxt - 0.04)*100), len(DB) - 1)
        while j < lim and DB[j] > max(pk - 9, top - 32): j += 1
        a, b = max(s['pk'], s['on'] + 0.05), min(j/100, nxt - 0.04)
        if b - a < 0.4: continue                                  # trzymana nuta = głos trwa >= 0,4 s po szczycie sylaby
        fr = [curve[f]*k_amp >= 0.3*s['open'] for f in range(int(math.ceil(a*FPS)), int(b*FPS - 2))]
        if not fr: continue
        n += 1; frac.append(np.mean(fr))
        if np.mean(fr) < 0.95: bad.append((round(s['on'], 2), round(b - a, 2), round(float(np.mean(fr)), 2)))
    return dict(held_notes=n, mean_open_fraction=round(float(np.mean(frac)), 3) if frac else None,
                notes_open_less_than_95pct=len(bad), worst=sorted(bad, key=lambda x: x[2])[:8])
R['held_notes'] = dict(lead=held_check(E.LEAD_SYLS, E.LEAD_DB, mouth), choir=held_check(E.CHOIR_SYLS, E.BACK_DB, cm))
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
    import signs as SG
    toks = [tk for tk, _ in SG._tokens((L['sec'], L['line']))]
    for k, (w, prev) in enumerate(zip(L['words'][1:], L['words'][:-1])):
        # początek frazy w środku wersu: po pauzie oddechowej albo po znaku interpunkcyjnym w tekście (np. '„Ogromny szacun” | do tego łaskawca')
        punct = k < len(toks) and toks[k][-1:] in ',.:;!?”"—'
        if w['t0'] - prev['t1'] > (0.25 if L['spoken'] else 0.2) or punct: line_starts.append(w['t0'])
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
# tekst w polu tablicy/dymka: najszerszy wiersz po 'wyskoku' słowa (+10%) i wysokość bloku z ogonkami/kreskami liter vs wnętrze pola
import signs as SG
fit = []
for sg in T.SIGNS:
    if sg.kind not in SG.BOXED: continue
    f = SG.font(sg.fname, sg.size); wmax = 0.0; top = 1e9; bot = -1e9
    for r, row in enumerate(sg.rows):
        b = __import__('skia').Rect(); f.measureText(' '.join(tk for tk, _ in row), __import__('skia').TextEncoding.kUTF8, b)
        wpop = max(f.measureText(tk) for tk, _ in row)*SG.POP
        wmax = max(wmax, b.width() + wpop); top = min(top, sg.base[r] + b.top()); bot = max(bot, sg.base[r] + b.bottom())
    fit.append(dict(line=list(sg.key), kind=sg.kind, margin_x_px=round((sg.w - wmax)/2, 1), margin_y_px=round(min(sg.h/2 + top, sg.h/2 - bot), 1)))
# napis w otworze sceny (poza nim zasłania go portal)
op_bad = 0; op_n = 0
for i in range(0, N, 3):
    t = i/FPS; s = T.shot_at(t)
    if s[2] != 'stage': continue
    cam = T.cam_at(t, s)
    opr = T.project_rect(cam, (S.OPEN_L, S.OPEN_T, S.OPEN_R, 0), S.D_PORTAL)
    for sg in T.SIGNS:
        if not sg.active(t) or sg.kind not in SG.BOXED or t < (sg.cut_in if sg.cut_in is not None else sg.t0 - 0.05): continue
        r = T.project_rect(cam, sg.rect(), sg.depth); op_n += 1
        if T.inter(r, opr)/max(T.area(r), 1) < 0.98: op_bad += 1
R['signs'] = dict(sign_frames_checked=checked, max_overlap_fraction_with_character=round(worst, 4), at=worst_at,
                  min_visible_fraction=round(vis_min, 3), min_visible_at=vis_at,
                  text_fits_box=dict(signs=len(fit), all_fit=all(f_['margin_x_px'] > 0 and f_['margin_y_px'] > 0 for f_ in fit),
                                     min_margin_x_px=min(f_['margin_x_px'] for f_ in fit), min_margin_y_px=min(f_['margin_y_px'] for f_ in fit)),
                  boxed_sign_frames_inside_stage_opening_pct=round(100*(1 - op_bad/max(op_n, 1)), 2),
                  placement=[dict(line=list(k), kind=kd, visibility=float(v), overlap=float(o)) for k, kd, v, o in T.SIGN_REPORT])
# ---------------------------------------------------------------- kadr: ucięte głowy, postaci kadru widoczne, POI w kadrze
part = 0; nfr = 0; part_at = []; subj_missing = 0; subj_missing_at = []; poi_n = 0; poi_out = 0; poi_out_at = []
for i in range(0, N, 3):
    t = i/FPS; s = T.shot_at(t)
    if s[2] != 'stage': continue
    cam = T.cam_at(t, s); nfr += 1
    specs = [k[1] for k in s[3] if isinstance(k[1], dict)]
    subj = set()
    for sp in specs: subj |= set(id(r) for r in T._subj_list(sp['subj'], t, (s[0], s[1])))
    D = np.mean([r.g('depth', t) for r in T.ROLES if id(r) in subj]) if subj else 0.0
    bad = False; seen = False
    for r in T.ROLES:
        a = r.actor(t)
        if a is None: continue
        hr = T.head_rect(a)
        if hr is None: continue
        pr = T.project_rect(cam, hr, a.depth); f = T.inter(pr, T.FRAME)/max(T.area(pr), 1)
        if id(r) in subj and f >= 0.5: seen = True
        if a.depth > D + 60 and id(r) not in subj: continue          # tło za kadrowaną grupą
        if 0.04 < f < 0.93 and not (r.span_at(t) and abs(a.y - r.g('y', t)) > 5 or abs(a.x - r.g('x', t)) > 40): bad = True
    if bad: part += 1; part_at.append(round(t, 1))
    if specs and not seen: subj_missing += 1; subj_missing_at.append(round(t, 1))
    tau = E.ease((t - s[0])/max(s[1] - s[0], 1e-6), 0.45)
    kk = s[3]; seg = [(kk[j], kk[j + 1]) for j in range(len(kk) - 1) if kk[j][0] <= tau <= kk[j + 1][0]] or [(kk[-1], kk[-1])]
    (ua, sa), (ub, sb) = seg[0]
    need = set(sa.get('poi', []) if isinstance(sa, dict) else []) & set(sb.get('poi', []) if isinstance(sb, dict) else [])
    for sp in specs[:1]:
        for n in sorted(need):
            (a_, b_), rect, d = T.POI[n]
            if a_ + 0.3 <= t <= b_ - 0.1:
                r = T.project_rect(cam, rect, d); poi_n += 1
                opr = T.project_rect(cam, (S.OPEN_L, S.OPEN_T, S.OPEN_R, 0), S.D_PORTAL)
                vis = T.inter(r, (max(0, opr[0]), max(0, opr[1]), min(E.W, opr[2]), min(E.H, opr[3])))/max(T.area(r), 1)
                if vis < 0.9: poi_out += 1; poi_out_at.append((round(t, 1), n, round(vis, 2)))
R['framing'] = dict(stage_frames_checked=nfr, frames_with_head_cut_by_edge=part, head_cut_at=part_at[:30],
                    frames_with_framed_subject_not_visible=subj_missing, subject_missing_at=subj_missing_at[:30],
                    poi_samples=poi_n, poi_samples_less_than_90pct_visible=poi_out, poi_out_at=sorted(set(poi_out_at))[:30],
                    heads_adjustments=[list(x) for x in T.HEADS_REPORT])
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
print(json.dumps({k: (v if k not in ('cuts', 'signs', 'choir', 'framing') else {kk: vv for kk, vv in v.items() if kk not in ('list', 'placement', 'counts', 'heads_adjustments')}) for k, v in R.items()}, ensure_ascii=False, indent=1))
