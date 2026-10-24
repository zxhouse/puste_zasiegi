"""'A pod spodem cisza, trochę jak męka' - widok zza krawędzi sceny (od strony lalkarzy).
v6: wszystko pracuje w rytmie - ręce lalkarzy w lalkach podbijają je na stopie, pręty idą na werblu, głowy zerkają na monitor,
za lalkarzami przechodzi inspicjent z latarką i słuchawkami, kable się kołyszą. Wariant 'band' (fałszujący fragment refrenu 2,
2:11-2:15): pod sceną gra 'orkiestra' - lalkarze jedną ręką prowadzą lalki, drugą grają (tuba, trąbka, tamburyn), dyryguje
inspicjent; z instrumentów wylatują krzywe, kwaśne nuty, na 'pęka' trąbka pęka na dwa dźwięki.
Nad krawędzią: plecy lalek w ciepłym świetle show. Pod krawędzią: lalkarze w czerni, pręty, monitor, zimne światło, cisza.
Własny 'świat' współrzędnych: górna krawędź ściany playboardu y=-150."""
import skia, math, numpy as np
import engine as E
from engine import smoothstep
from puppet import Material, fill, poly_path, col, shade, fur_fringe, superellipse
from gfx import card, draw_text, light_pool, beam, text_width
from signs import _tokens, _draw_tokens

EDGE = -150.0
def _layer(cv, cam, depth, fn):
    cv.save(); cam.apply(cv, depth); fn(); cv.restore()

_PICS = {}
def puppet_back(cv, x, jacket, skin, hair, seed, t, sway):
    """Lalka widziana od tyłu: marynarka, tył głowy z włosami (ruch razem z ręką lalkarza)."""
    cv.save(); cv.translate(x + sway, 0)
    body = [(-120, EDGE + 30), (-128, -330), (-100, -420), (0, -440), (100, -420), (128, -330), (120, EDGE + 30)]
    fill(cv, poly_path(body, True, True), Material(jacket, 'felt', 0.7, light=1.0, dark=0.55, seed=seed))
    H = superellipse(118, 100, 2.6, 80) + np.array([0, -540])
    fill(cv, poly_path(H, True, True), Material(skin, 'felt', 0.6, light=1.0, dark=0.6, seed=seed + 1))
    key = (seed, hair)
    if key not in _PICS:
        rec = skia.PictureRecorder(); c = rec.beginRecording(skia.Rect(-400, -900, 400, 200))
        cap = superellipse(124, 106, 2.4, 90) + np.array([0, -548])
        cap = cap[cap[:, 1] < -470]
        cap = cap[np.argsort(np.arctan2(cap[:, 1] + 548, cap[:, 0]))]
        fill(c, poly_path(np.vstack([cap, [[cap[-1, 0], -470], [cap[0, 0], -470]]]), True, True), Material(hair, 'felt', 0.5, light=1.1, dark=0.6, seed=seed + 2))
        fur_fringe(c, cap, col(hair), 26, 2.0, seed, 0.6, 4.0,
                   outward=lambda P: (P - np.array([0, -540]))/np.hypot(P[:, 0], P[:, 1] + 540)[:, None])
        rng = np.random.default_rng(seed)
        lp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeCap=skia.Paint.kRound_Cap)
        for k in range(60):                       # pasma włosów na tyle głowy
            x0 = rng.uniform(-100, 100); y0 = -640 + rng.uniform(0, 30)
            pa = skia.Path(); pa.moveTo(x0, y0); pa.quadTo(x0*1.1, y0 + 80, x0*1.15 + rng.normal(0, 8), -470 + rng.uniform(0, 20))
            lp.setColor4f(shade(col(hair), rng.uniform(0.7, 1.3))); lp.setStrokeWidth(rng.uniform(2, 4)); c.drawPath(pa, lp)
        _PICS[key] = rec.finishRecordingAsPicture()
    cv.drawPicture(_PICS[key])
    # ciepłe światło sceny z drugiej strony: obrys
    rim = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=7, Color4f=skia.Color4f(1, 0.82, 0.5, 0.55))
    rim.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 5))
    cv.drawPath(poly_path(H, True, True), rim)
    cv.restore()

def puppeteer(cv, x, t, ph, instr=None):
    """Lalkarz od tyłu (czarny strój, kaptur): jedna ręka w lalce nad krawędzią (podbija ją na stopie), druga trzyma pręt
    (rusza nim na werblu) albo - w wariancie 'band' - instrument."""
    dark = skia.Paint(AntiAlias=True, Color4f=col('#0a0a0f'))
    rim = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6, Color4f=skia.Color4f(0.35, 0.45, 0.95, 0.6))
    rim.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4))
    sway = 5*math.sin(t*0.7 + ph) + 10*E.beat_sway(t, 2.0, ph)
    bob = -26*E.kick(t, decay=0.16); rod = 60*E.snare(t, decay=0.18)
    look = 18*math.sin(t*0.45 + ph*2.0)                                  # zerka na monitor i z powrotem
    torso = [(x - 170, 1100), (x - 175, 260), (x - 120, 130), (x + 120, 130), (x + 175, 260), (x + 170, 1100)]
    cv.drawPath(poly_path(torso, True, True), dark); cv.drawPath(poly_path(torso[1:-1], False, True), rim)
    hx = x + sway*0.3 + look
    cv.drawCircle(hx, 40, 100, dark)
    cv.drawArc(skia.Rect(hx - 100, -60, hx + 100, 140), 195, 150, False, rim)
    if instr is None:                                                     # słuchawki na kapturze
        cv.drawArc(skia.Rect(hx - 104, -50, hx + 104, 150), 200, 140, False, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=9, Color4f=col('#26262e')))
    arm = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=78, StrokeCap=skia.Paint.kRound_Cap, Color4f=col('#0c0c12'))
    a1 = skia.Path(); a1.moveTo(x - 90, 190); a1.quadTo(x - 110 + sway, 20 + bob, x - 40 + sway, EDGE + 40 + bob)
    cv.drawPath(a1, arm); cv.drawPath(a1, rim)
    if instr is None:
        a2 = skia.Path(); a2.moveTo(x + 110, 200); a2.quadTo(x + 210, 120 - rod*0.5, x + 190 - sway, 10 - rod)
        cv.drawPath(a2, arm)
        cv.drawCircle(x + 190 - sway, -rod, 36, skia.Paint(AntiAlias=True, Color4f=col('#14141a')))
        cv.drawLine(x + 190 - sway, 10 - rod, x + 150 - sway*1.4, -420 - rod, skia.Paint(AntiAlias=True, StrokeWidth=5, Color4f=col('#3a3a46')))
    else:
        instrument(cv, instr, x, hx, t, ph, arm)
    return sway + 0*bob

BRASS = [col('#d9a93a'), col('#f4d27a'), col('#8a6418')]
def instrument(cv, kind, x, hx, t, ph, arm):
    """Instrumenty widziane zza pleców: tuba - czara nad ramieniem, trąbka - czara wystaje w bok, tamburyn - w uniesionej ręce."""
    g = lambda x0, y0, x1, y1: skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)], [c.toColor() for c in BRASS], [0, 0.45, 1])
    if kind == 'tuba':
        p = skia.Paint(AntiAlias=True); p.setShader(g(x + 40, -260, x + 300, -20))
        cv.drawOval(skia.Rect(x + 60, -280, x + 300, -150), p)                              # czara nad prawym barkiem
        cv.drawOval(skia.Rect(x + 90, -262, x + 270, -168), skia.Paint(AntiAlias=True, Color4f=col('#3a2a08')))
        cv.drawPath(poly_path([(x + 120, -170), (x + 230, -160), (x + 170, 140), (x + 110, 140)], True, False), p)
        a2 = skia.Path(); a2.moveTo(x + 110, 200); a2.quadTo(x + 230, 150, x + 170, 60); cv.drawPath(a2, arm)
    elif kind == 'trumpet':
        tilt = 8*math.sin(t*2.1 + ph)
        cv.save(); cv.translate(x + 150, -10); cv.rotate(-28 + tilt)
        p = skia.Paint(AntiAlias=True); p.setShader(g(0, -20, 260, 20))
        cv.drawRect(skia.Rect(0, -9, 200, 9), p)
        bell = skia.Path(); bell.moveTo(190, -10); bell.quadTo(250, -14, 280, -54); bell.lineTo(280, 54); bell.quadTo(250, 14, 190, 10); bell.close()
        cv.drawPath(bell, p); cv.drawOval(skia.Rect(268, -54, 292, 54), skia.Paint(AntiAlias=True, Color4f=col('#3a2a08')))
        for k in range(3): cv.drawRect(skia.Rect(60 + k*28, -26, 72 + k*28, -9), p)
        cv.restore()
        a2 = skia.Path(); a2.moveTo(x + 110, 200); a2.quadTo(x + 220, 120, x + 190, 10); cv.drawPath(a2, arm)
    elif kind == 'tambourine':
        up = -60*E.snare(t, decay=0.15) - 40*abs(math.sin(t*3.3 + ph))       # potrząsa - trochę obok rytmu
        cx_, cy_ = x + 230, -150 + up
        a2 = skia.Path(); a2.moveTo(x + 110, 200); a2.quadTo(x + 260, 60, cx_ - 10, cy_ + 40); cv.drawPath(a2, arm)
        cv.drawCircle(cx_, cy_, 78, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=22, Color4f=col('#a0522d')))
        cv.drawCircle(cx_, cy_, 68, skia.Paint(AntiAlias=True, Color4f=col('#f1e3c6')))
        for k in range(8):
            a = k*math.pi/4 + t*0.5
            cv.drawOval(skia.Rect(cx_ + 80*math.cos(a) - 12, cy_ + 80*math.sin(a) - 6, cx_ + 80*math.cos(a) + 12, cy_ + 80*math.sin(a) + 6), skia.Paint(AntiAlias=True, Color4f=BRASS[1]))

def sour_note(cv, x, y, s, a, wob, broken=0.0, color='#9bd16a'):
    """Krzywa, 'kwaśna' nuta: przechylona główka, falujący trzonek, zwichrowana chorągiewka; broken>0 - nuta pęka na pół."""
    c = col(color); c = skia.Color4f(c.fR, c.fG, c.fB, a)
    p = skia.Paint(AntiAlias=True, Color4f=c); st = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=7*s, Color4f=c, StrokeCap=skia.Paint.kRound_Cap)
    for half in ((0,) if broken <= 0 else (-1, 1)):
        cv.save(); cv.translate(x + half*broken*40*s, y + abs(half)*broken*30*s); cv.rotate(-20 + 25*wob + half*broken*25); cv.scale(s, s)
        cv.drawOval(skia.Rect(-26, -17, 26, 17), p)
        stem = skia.Path(); stem.moveTo(22, 0)
        for k in range(1, 7): stem.lineTo(22 + 9*math.sin(k*1.4 + wob*6), -k*18)
        cv.drawPath(stem, st)
        fl = skia.Path(); fl.moveTo(22 + 9*math.sin(6*1.4 + wob*6), -108); fl.quadTo(60, -80 + 20*wob, 44, -46); cv.drawPath(fl, st)
        cv.restore()

def notes_from(cv, x0, y0, t, t_start, seed, count=6, broken_at=None, color='#9bd16a'):
    rng = np.random.default_rng(seed)
    for k in range(count):
        ph = rng.uniform(0, 1); life = 1.6
        u = ((t - t_start)/life + ph) % 1.0
        if t - t_start < ph*life: continue
        x = x0 + rng.uniform(-80, 80) + 90*u*rng.choice([-1, 1]) + 30*math.sin(t*3 + k)
        y = y0 - 520*u
        a = min(1.0, u*6)*(1 - smoothstep((u - 0.7)/0.3))
        br = 0.0
        if broken_at is not None and 0 <= t - broken_at < 1.2: br = smoothstep((t - broken_at)/0.25)
        sour_note(cv, x, y, 0.9 + 0.4*rng.uniform(), a, math.sin(t*5 + k*2.1), br, color)

PEOPLE = [(-900, 0.3, '#6f7480', '#d6b48c', '#3b2a20', 11), (-250, 1.7, '#e8e4da', '#b9a3e3', '#ff6fb5', 21), (1150, 2.9, '#1f2a44', '#8e3f4a', '#e8e2d0', 31)]
BAND = ['tuba', 'trumpet', 'tambourine']

def stage_manager(cv, t, t0, x0, x1, dur, band=False):
    """Inspicjent w czerni (twarzą do nas, za lalkarzami): idzie z latarką i słuchawkami albo - w 'band' - dyryguje batutą."""
    u = min(max((t - t0)/dur, 0.0), 1.0)
    x = x0 + (x1 - x0)*u if not band else x0
    step = abs(math.sin(t*6.0))*10 if not band else 0.0
    dark = skia.Paint(AntiAlias=True, Color4f=col('#0d0d14'))
    cv.drawPath(poly_path([(x - 120, 900), (x - 130, 230 - step), (x - 80, 120 - step), (x + 80, 120 - step), (x + 130, 230 - step), (x + 120, 900)], True, True), dark)
    face = skia.Paint(AntiAlias=True, Color4f=col('#c9a58a')); cv.drawOval(skia.Rect(x - 62, -40 - step, x + 62, 110 - step), face)
    cv.drawArc(skia.Rect(x - 70, -52 - step, x + 70, 120 - step), 180, 180, True, dark)                      # czapka
    hs = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8, Color4f=col('#2c2c34'))
    cv.drawArc(skia.Rect(x - 74, -30 - step, x + 74, 110 - step), 190, 160, False, hs); cv.drawLine(x + 66, 50 - step, x + 30, 92 - step, hs)
    ey = 30 - step; sq = 0.6 if band else 0.0                                                                  # oczy (przy fałszu zmrużone)
    for sx in (-1, 1):
        if sq > 0: cv.drawLine(x + sx*26 - 10, ey, x + sx*26 + 10, ey + 4*sx, skia.Paint(AntiAlias=True, StrokeWidth=5, Color4f=col('#2a1a10')))
        else: cv.drawCircle(x + sx*26, ey, 7, skia.Paint(AntiAlias=True, Color4f=col('#2a1a10')))
    mp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=col('#5a2a1a'))
    if band: cv.drawArc(skia.Rect(x - 22, 70 - step, x + 22, 96 - step), 200, 140, False, mp)                    # skrzywienie
    else: cv.drawLine(x - 16, 80 - step, x + 16, 80 - step, mp)
    arm = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=56, StrokeCap=skia.Paint.kRound_Cap, Color4f=col('#101018'))
    if band:                                                                                                  # batuta - nie w takt
        a = math.sin(t*2*math.pi*1.13)*40 - 20
        hx, hy = x + 150 + 60*math.cos(math.radians(a)), 60 + 80*math.sin(math.radians(a))
        cv.drawLine(x + 80, 200, hx, hy, arm)
        cv.drawLine(hx, hy, hx + 120*math.cos(math.radians(a - 40)), hy + 120*math.sin(math.radians(a - 40)), skia.Paint(AntiAlias=True, StrokeWidth=6, Color4f=col('#f2efe6')))
    else:                                                                                                     # latarka
        cv.drawLine(x + 80, 200, x + 170, 260, arm)
        sw = 0.4*math.sin(t*1.7)
        beam(cv, x + 190, 270, x + 190 + 900*math.cos(0.5 + sw), 270 + 900*math.sin(0.5 + sw), 18, 180, (1.0, 0.95, 0.75), 0.22)
        cv.drawCircle(x + 190, 270, 16, skia.Paint(AntiAlias=True, Color4f=col('#fff3c4')))

def render_under(cv, t, cam, variant='quiet', line=(4, 3), t0=None):
    cv.clear(skia.Color4f(0.02, 0.02, 0.035, 1))
    def back():
        # nad krawędzią: jasna scena (od tyłu) - ciepłe światło, snopy reflektorów
        g = skia.GradientShader.MakeLinear([skia.Point(0, -1300), skia.Point(0, EDGE)], [col('#2a1630').toColor(), col('#ffcf8a').toColor()])
        p = skia.Paint(); p.setShader(g); cv.drawRect(skia.Rect(-3000, -1600, 3000, EDGE), p)
        for k, x in enumerate((-1500, -500, 500, 1500)):
            beam(cv, x, -1500, x + 200*math.sin(t*0.6 + k), EDGE, 40, 260, (1, 0.85, 0.6), 0.16)
        # pod krawędzią: ciemne kulisy
        cv.drawRect(skia.Rect(-3000, EDGE, 3000, 1800), skia.Paint(Color4f=col('#07070c')))
    _layer(cv, cam, 400, back)
    # plecy lalek nad krawędzią (poruszają się razem z rękami lalkarzy)
    def puppets():
        for x, ph, jk, sk, hr, sd in PEOPLE:
            sway = 5*math.sin(t*0.7 + ph)
            puppet_back(cv, x - 40, jk, sk, hr, sd, t, sway)
    _layer(cv, cam, 60, puppets)
    # ściana playboardu od tyłu: surowa sklejka, zastrzały, kartka z cue, zegar, wers kredą
    def wall():
        r = skia.Path(); r.addRect(skia.Rect(-3000, EDGE, 3000, 1800))
        fill(cv, r, Material('#5f5040', 'card', 0.9, light=0.95, dark=0.6, seed=502))
        cv.drawRect(skia.Rect(-3000, EDGE, 3000, EDGE + 26), skia.Paint(Color4f=col('#3e352b')))
        for x in range(-2600, 2700, 520):
            cv.drawLine(x, EDGE + 26, x + 180, 1800, skia.Paint(AntiAlias=True, StrokeWidth=30, Color4f=col('#4a3e31')))
        card(cv, (-1480, 120, -1260, 300), '#f7e27a', 3, 'card', 503, 0.6)
        draw_text(cv, 'CUE 47', -1370, 220, 'hand', 44, '#333333')
        cv.drawCircle(1500, 300, 90, skia.Paint(AntiAlias=True, Color4f=col('#e8e2d0')))
        cv.drawLine(1500, 300, 1500 + 60*math.sin(t*0.5), 300 - 60*math.cos(t*0.5), skia.Paint(AntiAlias=True, StrokeWidth=6, Color4f=col('#222222')))
        toks = _tokens(line); hf = (len(toks) + 1)//2
        _draw_tokens(cv, [toks[:hf], toks[hf:]], t, 'hand', 84, '#ecebe4', 470, 230, 108, pop=False)
    _layer(cv, cam, 160, wall)
    # monitor podglądu (pokazuje show) - stoi po lewej
    def monitor():
        cv.drawLine(-1500, 120, -1500, 1200, skia.Paint(AntiAlias=True, StrokeWidth=14, Color4f=col('#222228')))
        card(cv, (-1720, -120, -1280, 160), '#1a1a1f', 10, 'card', 501, 0.5)
        g = skia.GradientShader.MakeLinear([skia.Point(0, -100), skia.Point(0, 140)], [col('#3a0f4f').toColor(), col('#7a3db8').toColor()])
        p = skia.Paint(); p.setShader(g); cv.drawRect(skia.Rect(-1700, -100, -1300, 140), p)
        for k in range(5):
            cv.drawCircle(-1660 + k*80, 60 - 12*math.sin(t*3 + k), 20, skia.Paint(AntiAlias=True, Color4f=col(['#d6b48c', '#e4c65c', '#f2a1c0', '#73b7a6', '#b9a3e3'][k])))
        light_pool(cv, -1500, 20, 480, 340, (0.6, 0.5, 1.0), 0.25)
    _layer(cv, cam, 30, monitor)
    # inspicjent (za lalkarzami): przechodzi z latarką / dyryguje
    T0 = t0 if t0 is not None else t
    _layer(cv, cam, 90, lambda: stage_manager(cv, t, T0, -1700, 1700, 3.2, band=(variant == 'band')))
    # kable pod sceną (kołyszą się)
    def cables():
        cp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=9, Color4f=col('#15151c'))
        for k, x in enumerate((-1300, -600, 300, 900)):
            pa = skia.Path(); pa.moveTo(x, EDGE + 30)
            pa.quadTo(x + 120 + 40*math.sin(t*1.2 + k), EDGE + 420, x + 260, EDGE + 60); cv.drawPath(pa, cp)
    _layer(cv, cam, 120, cables)
    # lalkarze (od tyłu)
    def people():
        for k, (x, ph, *_) in enumerate(PEOPLE): puppeteer(cv, x, t, ph, BAND[k] if variant == 'band' else None)
    _layer(cv, cam, 0, people)
    if variant == 'band':                    # kwaśne nuty z instrumentów; na 'pęka' nuty pękają
        import timeline as TL
        crack = TL.wt(TL.CH2, 1, 5)
        def notes():
            notes_from(cv, PEOPLE[0][0] + 180, -240, t, T0, 3, 6, None, '#9bd16a')
            notes_from(cv, PEOPLE[1][0] + 430, -140, t, T0 + 0.3, 5, 6, crack, '#c58cf0')
            notes_from(cv, PEOPLE[2][0] + 230, -260, t, T0 + 0.6, 7, 5, None, '#f2c14e')
        _layer(cv, cam, -10, notes)
    # zimne światło robocze i drobinki kurzu
    def work_light():
        light_pool(cv, -300, 300, 1500, 900, (0.3, 0.4, 0.85), 0.22)
        rng = np.random.default_rng(9)
        for k in range(80):
            x = rng.uniform(-1800, 1800); y = (rng.uniform(-200, 900) + t*14*(0.5 + rng.uniform())) % 1100 - 200
            cv.drawCircle(x, y, 2.5, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.7, 0.75, 1, 0.35)))
    _layer(cv, cam, -20, work_light)
