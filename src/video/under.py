"""'A pod spodem cisza, trochę jak męka' - widok zza krawędzi sceny (od strony lalkarzy).
Nad krawędzią: plecy lalek w ciepłym świetle show. Pod krawędzią: lalkarze w czerni, pręty, monitor, zimne światło, cisza.
Własny 'świat' współrzędnych: górna krawędź ściany playboardu y=-150."""
import skia, math, numpy as np
import engine as E
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

def puppeteer(cv, x, t, ph):
    """Lalkarz od tyłu (czarny strój, kaptur): jedna ręka w lalce nad krawędzią, druga trzyma pręt."""
    dark = skia.Paint(AntiAlias=True, Color4f=col('#0a0a0f'))
    rim = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6, Color4f=skia.Color4f(0.35, 0.45, 0.95, 0.6))
    rim.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4))
    sway = 5*math.sin(t*0.7 + ph)
    torso = [(x - 170, 1100), (x - 175, 260), (x - 120, 130), (x + 120, 130), (x + 175, 260), (x + 170, 1100)]
    cv.drawPath(poly_path(torso, True, True), dark); cv.drawPath(poly_path(torso[1:-1], False, True), rim)
    cv.drawCircle(x + sway*0.3, 40, 100, dark)
    cv.drawArc(skia.Rect(x + sway*0.3 - 100, -60, x + sway*0.3 + 100, 140), 195, 150, False, rim)
    arm = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=78, StrokeCap=skia.Paint.kRound_Cap, Color4f=col('#0c0c12'))
    a1 = skia.Path(); a1.moveTo(x - 90, 190); a1.quadTo(x - 110 + sway, 20, x - 40 + sway, EDGE + 40)
    cv.drawPath(a1, arm); cv.drawPath(a1, rim)
    a2 = skia.Path(); a2.moveTo(x + 110, 200); a2.quadTo(x + 210, 120, x + 190 - sway, 10)
    cv.drawPath(a2, arm)
    cv.drawCircle(x + 190 - sway, 0, 36, skia.Paint(AntiAlias=True, Color4f=col('#14141a')))
    cv.drawLine(x + 190 - sway, 10, x + 150 - sway*1.4, -420, skia.Paint(AntiAlias=True, StrokeWidth=5, Color4f=col('#3a3a46')))
    return sway

PEOPLE = [(-900, 0.3, '#6f7480', '#d6b48c', '#3b2a20', 11), (-250, 1.7, '#e8e4da', '#b9a3e3', '#ff6fb5', 21), (1150, 2.9, '#1f2a44', '#8e3f4a', '#e8e2d0', 31)]

def render_under(cv, t, cam):
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
        toks = _tokens((4, 3))
        _draw_tokens(cv, [toks[:4], toks[4:]], t, 'hand', 84, '#ecebe4', 470, 230, 108, pop=False)
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
    # lalkarze (od tyłu)
    def people():
        for x, ph, *_ in PEOPLE: puppeteer(cv, x, t, ph)
    _layer(cv, cam, 0, people)
    # zimne światło robocze i drobinki kurzu
    def work_light():
        light_pool(cv, -300, 300, 1500, 900, (0.3, 0.4, 0.85), 0.22)
        rng = np.random.default_rng(9)
        for k in range(80):
            x = rng.uniform(-1800, 1800); y = (rng.uniform(-200, 900) + t*14*(0.5 + rng.uniform())) % 1100 - 200
            cv.drawCircle(x, y, 2.5, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.7, 0.75, 1, 0.35)))
    _layer(cv, cam, -20, work_light)
