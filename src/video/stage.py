"""Scena lalkowego show: studio TV, portal z żarówkami, kurtyna, krawędź sceny (playboard), dekoracje z tektury.
Współrzędne świata: płaszczyzna sceny depth=0, górna krawędź playboardu y=0, otwór sceny x∈[-1050,1050], y∈[-780,0]."""
import skia, math, numpy as np, functools
from puppet import Material, fill, poly_path, col, shade, mix, fur_fringe
from gfx import card, draw_text, light_pool, beam, bulb, drop_shadow, font, text_width
import engine as E
import textures as TX

D_BACK, D_MID, D_RISER, D_PLAY, D_CURT, D_PORTAL, D_TRUSS = 380.0, 170.0, 70.0, -30.0, -70.0, -130.0, -260.0
OPEN_L, OPEN_R, OPEN_T = -1050, 1050, -780

def _rec(fn, bounds=(-2600, -2000, 2600, 1400)):
    rec = skia.PictureRecorder(); c = rec.beginRecording(skia.Rect(*bounds)); fn(c); return rec.finishRecordingAsPicture()
_PICS = {}
def cached(key, fn, bounds=(-2600, -2000, 2600, 1400)):
    if key not in _PICS: _PICS[key] = _rec(fn, bounds)
    return _PICS[key]

# ------------------------------------------------------------------ studio TV wokół sceny
def studio(cv, t, lights=1.0):
    def bg(c):
        g = skia.GradientShader.MakeLinear([skia.Point(0, -2000), skia.Point(0, 1400)], [col('#0d0a12').toColor(), col('#1a1220').toColor(), col('#0a0809').toColor()], [0, 0.6, 1])
        p = skia.Paint(); p.setShader(g); c.drawRect(skia.Rect(-3000, -2400, 3000, 1800), p)
        # podłoga studia
        c.drawRect(skia.Rect(-3000, 420, 3000, 1800), skia.Paint(Color4f=col('#141016')))
        for i in range(-30, 31):
            c.drawLine(i*100, 420, i*100*1.8, 1800, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.03), StrokeWidth=2))
    cv.drawPicture(cached('studio_bg', bg, (-3000, -2400, 3000, 1800)))

def truss(cv, t, lights=1.0):
    def tr(c):
        p = skia.Paint(AntiAlias=True, Color4f=col('#3b3b44'), StrokeWidth=7, Style=skia.Paint.kStroke_Style)
        y0, y1 = -1330, -1270
        c.drawLine(-2200, y0, 2200, y0, p); c.drawLine(-2200, y1, 2200, y1, p)
        for x in range(-2200, 2201, 60): c.drawLine(x, y0, x + 30, y1, p); c.drawLine(x + 30, y1, x + 60, y0, p)
        for x in range(-1800, 1801, 300):
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x - 34, y1, x + 34, y1 + 70), 12, 12), skia.Paint(AntiAlias=True, Color4f=col('#22222a')))
            c.drawCircle(x, y1 + 72, 26, skia.Paint(AntiAlias=True, Color4f=col('#e8e0c8')))
    cv.drawPicture(cached('truss', tr))
    for i, x in enumerate(range(-1800, 1801, 300)):
        light_pool(cv, x, -1198, 120, 120, (1, 0.9, 0.7), 0.25*lights)

# ------------------------------------------------------------------ portal z żarówkami i marquee
def portal(cv, t, chase=0.0, bulbs_on=1.0, marquee_text=None):
    def frame(c):
        p = skia.Path(); p.setFillType(skia.PathFillType.kEvenOdd)
        p.addRect(skia.Rect(-1260, -1080, 1260, 470)); p.addRRect(skia.RRect.MakeRectXY(skia.Rect(OPEN_L, OPEN_T, OPEN_R, 470), 40, 40))
        fill(c, p, Material('#16525e', 'card', 0.9, light=1.15, dark=0.7, seed=4))
        # złote listwy
        g = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=18, Color4f=col('#c99a3a'))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(OPEN_L - 14, OPEN_T - 14, OPEN_R + 14, 484), 52, 52), g)
        g2 = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6, Color4f=col('#e8c46a'))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-1230, -1050, 1230, 470), 30, 30), g2)
        # tablica marquee nad otworem
        card(c, (-560, -1040, 560, -830), '#2a1a2e', 26, 'card', 6, 0.5)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-545, -1025, 545, -845), 20, 20), skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8, Color4f=col('#c99a3a')))
        # ornamenty na filarach
        for sx in (-1, 1):
            for k in range(5):
                y = -700 + k*260
                c.drawCircle(sx*1155, y, 34, skia.Paint(AntiAlias=True, Color4f=col('#c99a3a')))
                c.drawCircle(sx*1155, y, 20, skia.Paint(AntiAlias=True, Color4f=col('#8e1f2b')))
    cv.drawPicture(cached('portal', frame))
    # żarówki wokół otworu (pogoń na bitach)
    n = 0
    pts = []
    for x in np.linspace(OPEN_L + 40, OPEN_R - 40, 22): pts.append((x, OPEN_T - 50))
    for y in np.linspace(OPEN_T + 60, 400, 9): pts.append((OPEN_L - 55, y)); pts.append((OPEN_R + 55, y))
    for i, (x, y) in enumerate(pts):
        on = bulbs_on*(0.35 + 0.65*(0.5 + 0.5*math.cos(2*math.pi*(i/3.0 - chase))))
        bulb(cv, x, y, 13, on)
    if marquee_text is not None:
        marquee_text(cv)

# ------------------------------------------------------------------ playboard (krawędź sceny)
def playboard(cv, t, color='#26304f', trim='#c99a3a', bulbs=0.0):
    def pb(c):
        r = skia.Path(); r.addRect(skia.Rect(-1500, 0, 1500, 470))
        fill(c, r, Material(color, 'felt', 0.9, light=1.1, dark=0.75, seed=8))
        c.drawRect(skia.Rect(-1500, 0, 1500, 16), skia.Paint(Color4f=col(trim)))
        c.drawRect(skia.Rect(-1500, 16, 1500, 24), skia.Paint(Color4f=shade(col(trim), 0.6)))
        # malowany wzór (romby)
        for i in range(-14, 15):
            x = i*105
            pts = [(x, 120), (x + 30, 160), (x, 200), (x - 30, 160)]
            c.drawPath(poly_path(pts, True, False), skia.Paint(AntiAlias=True, Color4f=col('#c99a3a', 0.55)))
        g = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 60)], [skia.Color4f(0, 0, 0, 0.0).toColor(), skia.Color4f(0, 0, 0, 0.0).toColor()])
    cv.drawPicture(cached(('pb', color), pb))

# ------------------------------------------------------------------ kurtyna (aksamit, fałdy, frędzle)
def curtain(cv, t, open_amt=0.0, sway=0.0, color='#8e1424', tint=None):
    """open_amt 0 = zamknięta, 1 = całkiem rozsunięta. Fałdy zagęszczają się przy zsuwaniu."""
    def half(c, sgn):
        pass
    top, bot = OPEN_T - 60, 470
    base = col(color)
    for sgn in (-1, 1):
        inner = sgn*(8 + open_amt*1000)          # wewnętrzna krawędź połowy
        outer = sgn*1120
        width = abs(outer - inner)
        nf = 9
        cv.save()
        xs = np.linspace(inner, outer, nf*8 + 1)
        # obrys z falą na dole
        for k in range(nf):
            a = inner + (outer - inner)*k/nf; b = inner + (outer - inner)*(k + 1)/nf
            if abs(b - a) < 1: continue
            sw = math.sin(t*1.3 + k*0.9 + sgn)*sway*6
            rect = skia.Rect(min(a, b) + sw*0.3, top, max(a, b) + sw*0.3, bot + 12*math.sin(k*1.7 + t))
            g = skia.GradientShader.MakeLinear([skia.Point(min(a, b), 0), skia.Point(max(a, b), 0)],
                                               [shade(base, 0.45).toColor(), shade(base, 1.18).toColor(), base.toColor(), shade(base, 0.5).toColor()], [0, 0.35, 0.6, 1])
            p = skia.Paint(AntiAlias=True); p.setShader(g)
            cv.drawRect(rect, p)
            tp = Material(base, 'velvet', 1.2, seed=5).tex_paint(); cv.drawRect(rect, tp)
        # złote frędzle na dole
        fr = skia.Paint(AntiAlias=True, Color4f=col('#d8a83c'), StrokeWidth=4)
        x0, x1 = sorted([inner, outer])
        for x in np.arange(x0, x1, 14):
            cv.drawLine(x, bot - 6, x + 2, bot + 34, fr)
        cv.drawRect(skia.Rect(x0, bot - 16, x1, bot - 2), skia.Paint(Color4f=col('#c99a3a')))
        # cień na wewnętrznej krawędzi
        sp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.45)); sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 20))
        cv.drawRect(skia.Rect(inner - (30 if sgn > 0 else 0), top, inner + (0 if sgn > 0 else 30), bot), sp)
        cv.restore()
    # lambrekin (stała falbana u góry)
    def val(c):
        pts = [(-1150, OPEN_T - 80)]
        for i in range(13):
            x0 = -1150 + i*2300/13; x1 = x0 + 2300/13
            pts += [(x0 + 2300/26, OPEN_T + 70), (x1, OPEN_T - 10)]
        pts += [(1150, OPEN_T - 80)]
        pp = poly_path(pts, True, True)
        fill(c, pp, Material(shade(base, 0.85), 'velvet', 1.2, seed=6))
        c.drawPath(poly_path(pts[1:-1], False, True), skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=10, Color4f=col('#c99a3a')))
    cv.drawPicture(cached(('valance', color), val))

# ------------------------------------------------------------------ dekoracje (tło depth=D_BACK, rekwizyty depth=D_MID)
def wall(c, color, stripe=None, y0=-1300, y1=480, x0=-1700, x1=1700):
    fill(c, skia.Path().addRect(skia.Rect(x0, y0, x1, y1)) if False else _rect(x0, y0, x1, y1), Material(color, 'card', 1.1, light=1.08, dark=0.86, seed=12))
    if stripe:
        for x in np.arange(x0, x1, 120):
            c.drawRect(skia.Rect(x, y0, x + 55, y1), skia.Paint(Color4f=col(stripe, 0.35)))
def _rect(x0, y0, x1, y1):
    p = skia.Path(); p.addRect(skia.Rect(x0, y0, x1, y1)); return p

def set_kitchen_back(c):
    wall(c, '#f2dfae', '#e7cd8e')
    c.drawRect(skia.Rect(-1700, 140, 1700, 480), skia.Paint(Color4f=col('#8b5e3c')))       # boazeria
    # okno
    card(c, (-760, -900, -160, -330), '#f6f1e4', 16, 'card', 21, 0.6)
    g = skia.GradientShader.MakeLinear([skia.Point(0, -870), skia.Point(0, -360)], [col('#7fc8f8').toColor(), col('#ffe6a8').toColor()])
    p = skia.Paint(); p.setShader(g); c.drawRect(skia.Rect(-730, -870, -190, -360), p)
    for x in (-460,): c.drawRect(skia.Rect(x - 10, -870, x + 10, -360), skia.Paint(Color4f=col('#f6f1e4')))
    c.drawRect(skia.Rect(-730, -625, -190, -605), skia.Paint(Color4f=col('#f6f1e4')))
    # półka z kubkami
    card(c, (240, -620, 860, -585), '#9a6b45', 6, 'card', 22, 0.6)
    for i, cc in enumerate(['#e05d5d', '#4f86c6', '#f2c14e', '#6cbf84']):
        x = 300 + i*150
        card(c, (x, -720, x + 80, -620), cc, 12, 'card', 23 + i, 0.6)
        c.drawArc(skia.Rect(x + 66, -700, x + 110, -650), -90, 180, False, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=10, Color4f=col(cc)))
    # kalendarz
    card(c, (980, -900, 1240, -600), '#ffffff', 8, 'card', 25, 0.6)
    c.drawRect(skia.Rect(980, -900, 1240, -830), skia.Paint(Color4f=col('#d64545')))
    draw_text(c, 'PONIEDZIAŁEK', 1110, -853, 'block2', 30, '#ffffff')
    draw_text(c, '7:30', 1110, -680, 'block', 110, '#333333')

def set_kitchen_mid(c):
    # ekspres do kawy (tektura)
    card(c, (620, -330, 900, 40), '#4a4a52', 20, 'card', 31, 0.5)
    card(c, (650, -300, 870, -200), '#2c2c33', 10, 'card', 32, 0.5)
    c.drawCircle(760, -250, 26, skia.Paint(AntiAlias=True, Color4f=col('#ff5a5a')))
    card(c, (700, -150, 820, -120), '#9a9aa5', 6, 'card', 33, 0.5)
    # sztaluga z 'WIELKI PLAN'
    lp = skia.Paint(AntiAlias=True, StrokeWidth=14, Color4f=col('#7a5232'))
    c.drawLine(-980, 40, -880, -560, lp); c.drawLine(-620, 40, -720, -560, lp)
    card(c, (-1020, -620, -580, -290), '#fbfaf5', 10, 'card', 34, 0.6, wobble=3)
    draw_text(c, 'WIELKI PLAN', -800, -560, 'hand', 44, '#1f3b73')
    pp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8, Color4f=col('#2e8b57'), StrokeCap=skia.Paint.kRound_Cap)
    path = skia.Path(); path.moveTo(-990, -330); path.lineTo(-900, -380); path.lineTo(-830, -360); path.lineTo(-730, -470); path.lineTo(-640, -520)
    c.drawPath(path, pp)
    c.drawLine(-640, -520, -675, -515, pp); c.drawLine(-640, -520, -650, -488, pp)

def set_office_back(c):
    wall(c, '#c9d6df', None)
    for i in range(5):
        x = -1450 + i*620
        card(c, (x, -1000, x + 420, -560), '#9fb3c8', 10, 'card', 40 + i, 0.6)
        g = skia.GradientShader.MakeLinear([skia.Point(0, -980), skia.Point(0, -580)], [col('#3e6c94').toColor(), col('#b9d7ea').toColor()])
        p = skia.Paint(); p.setShader(g); c.drawRect(skia.Rect(x + 20, -980, x + 400, -580), p)
        for k in range(4):   # wieżowce za oknem
            bx = x + 40 + k*90; c.drawRect(skia.Rect(bx, -800 + (k % 2)*60, bx + 60, -580), skia.Paint(Color4f=col('#5d7a95')))
    c.drawRect(skia.Rect(-1700, 120, 1700, 480), skia.Paint(Color4f=col('#7c8a96')))
    draw_text(c, 'SYNERGIA CORP.', 0, -380, 'block', 120, '#8fa4b6')

def set_office_mid(c):
    # ścianki boksów open space (przed chórem w okienkach)
    for i in range(4):
        x = -900 + i*480
        card(c, (x, -250, x + 360, 60), '#6f8597', 14, 'felt', 50 + i, 0.55)
        c.drawRect(skia.Rect(x, -250, x + 360, -232), skia.Paint(Color4f=col('#4a5866')))

def set_conf_back(c):
    wall(c, '#14213d', None)
    for j in range(9):
        for i in range(9):
            x = -1500 + i*380 + (j % 2)*190; y = -1150 + j*170
            draw_text(c, 'SYNERGIA', x, y, 'block', 44, '#fca311' if (i + j) % 2 == 0 else '#e5e5e5')
            draw_text(c, '2026', x, y + 42, 'block2', 30, '#e5e5e5' if (i + j) % 2 == 0 else '#fca311')
    card(c, (-700, -1130, 700, -930), '#fca311', 20, 'card', 61, 0.6)
    draw_text(c, 'KONFERENCJA LIDERÓW', 0, -1050, 'block', 76, '#14213d')
    draw_text(c, 'SYNERGII I WIZJI 2026', 0, -965, 'block2', 58, '#14213d')

def set_conf_mid(c):
    for sx in (-1, 1):
        x = sx*1180
        card(c, (x - 170, -900, x + 170, 60), '#e5e5e5', 10, 'card', 70 + (sx > 0), 0.6)
        draw_text(c, 'LIDERZY', x, -760, 'block', 64, '#14213d'); draw_text(c, 'JUTRA', x, -690, 'block', 64, '#fca311')
        c.drawCircle(x, -450, 110, skia.Paint(AntiAlias=True, Color4f=col('#fca311')))
        pts = [(x + (80 if k % 2 == 0 else 36)*math.cos(-math.pi/2 + k*math.pi/5), -450 + (80 if k % 2 == 0 else 36)*math.sin(-math.pi/2 + k*math.pi/5)) for k in range(10)]
        c.drawPath(poly_path(pts, True, False), skia.Paint(AntiAlias=True, Color4f=col('#14213d')))

def set_show_back(c):
    g = skia.GradientShader.MakeRadial(skia.Point(0, -500), 1800, [col('#3a0f4f').toColor(), col('#12051c').toColor()])
    p = skia.Paint(); p.setShader(g); c.drawRect(skia.Rect(-1800, -1400, 1800, 600), p)

def set_show_rays(c):   # promienie sunburst (osobno, bo się obracają)
    for i in range(24):
        a0 = i*2*math.pi/24; a1 = a0 + math.pi/24
        pts = [(0, 0), (2600*math.cos(a0), 2600*math.sin(a0)), (2600*math.cos(a1), 2600*math.sin(a1))]
        c.drawPath(poly_path(pts, True, False), skia.Paint(AntiAlias=True, Color4f=col('#ff4f8b' if i % 2 else '#ff9f1c', 0.22)))

def set_show_riser(c):
    for k, (y, w) in enumerate([(-120, 1050), (-40, 1120)]):
        card(c, (-w, y, w, y + 90), ['#5b2a86', '#7a3db8'][k], 12, 'card', 80 + k, 0.6)
        for x in np.linspace(-w + 40, w - 40, 26):
            c.drawCircle(x, y + 45, 9, skia.Paint(AntiAlias=True, Color4f=col('#ffd166')))

def set_studio_g_back(c):
    wall(c, '#f8d7e3', '#f3c4d6')
    card(c, (520, -900, 1300, -860), '#c98b5a', 6, 'card', 91, 0.6)
    for i in range(9):
        x = 540 + i*82; hh = 140 + (i*37) % 60
        card(c, (x, -860 - hh, x + 70, -860), ['#ff6fb5', '#6c5ce7', '#00b894', '#fdcb6e', '#e17055'][i % 5], 6, 'card', 92 + i, 0.6)
    draw_text(c, '#wdzięczność', -620, -820, 'script', 120, '#ff3c8e', shadow=(0, 0, 0.0))
    card(c, (-1200, -560, -880, -260), '#fff8e7', 10, 'card', 99, 0.6)
    draw_text(c, 'TOP 1%', -1040, -440, 'block', 60, '#c99a3a'); draw_text(c, 'GŁOSÓW', -1040, -380, 'block2', 40, '#c99a3a')

def set_studio_g_mid(c):
    # ring light na statywie
    lp = skia.Paint(AntiAlias=True, StrokeWidth=10, Color4f=col('#333333'))
    c.drawLine(-760, -300, -760, 60, lp)

def set_road_back(c):
    g = skia.GradientShader.MakeLinear([skia.Point(0, -1300), skia.Point(0, -300)], [col('#ff9a62').toColor(), col('#ffd9a0').toColor()])
    p = skia.Paint(); p.setShader(g); c.drawRect(skia.Rect(-1800, -1400, 1800, -300), p)
    c.drawCircle(500, -560, 160, skia.Paint(AntiAlias=True, Color4f=col('#fff1c1')))
    c.drawRect(skia.Rect(-1800, -320, 1800, 600), skia.Paint(Color4f=col('#7aa35a')))
    road = poly_path([(-60, -320), (60, -320), (900, 600), (-900, 600)], True, False)
    fill(c, road, Material('#8d8d8d', 'card', 1.0, seed=101))
    c.save(); c.clipPath(road, doAntiAlias=True)
    rng = np.random.default_rng(7)
    for row in range(40):
        y = -320 + (row/40)**1.6*920; hgt = 4 + (row/40)**1.6*38
        w = 10 + (row/40)**1.6*70
        off = (row % 2)*w/2
        for x in np.arange(-900 - off, 900, w):
            sh = 0.8 + rng.uniform(0, 0.35)
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x + 2, y, x + w - 2, y + hgt - 2), hgt*0.3, hgt*0.3), skia.Paint(AntiAlias=True, Color4f=shade(col('#9c968c'), sh)))
    c.restore()
    # drogowskaz
    lp = skia.Paint(AntiAlias=True, StrokeWidth=22, Color4f=col('#6b4b2a')); c.drawLine(-900, -800, -900, 60, lp)
    card(c, (-1180, -840, -640, -720), '#f4e9d0', 8, 'card', 102, 0.6)
    draw_text(c, 'NOWA DROGA →', -910, -760, 'sign', 62, '#3a2a1a')

def set_heaven_back(c):
    g = skia.GradientShader.MakeLinear([skia.Point(0, -1300), skia.Point(0, 500)], [col('#9fd3ff').toColor(), col('#fff7e6').toColor()])
    p = skia.Paint(); p.setShader(g); c.drawRect(skia.Rect(-1800, -1400, 1800, 600), p)
    rng = np.random.default_rng(3)
    for k in range(14):
        x = rng.uniform(-1500, 1500); y = rng.uniform(-1100, 100); s = rng.uniform(0.6, 1.3)
        for j in range(6):
            c.drawCircle(x + (j - 2.5)*55*s, y + abs(j - 2.5)*10*s, (60 - abs(j - 2.5)*8)*s, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.92)))
    # złota brama z boksów
    for sx in (-1, 1):
        card(c, (sx*700 - 90, -900, sx*700 + 90, 200), '#e9c46a', 10, 'card', 111, 0.6)
    card(c, (-790, -1000, 790, -880), '#e9c46a', 16, 'card', 112, 0.6)
    draw_text(c, 'KORPORACYJNY RAJ', 0, -915, 'sign', 76, '#7a5c12')

def set_wood_back(c):
    c.drawRect(skia.Rect(-1800, -1400, 1800, 600), skia.Paint(Color4f=col('#2a1a10')))
    rng = np.random.default_rng(5)
    for i, x in enumerate(np.arange(-1700, 1700, 70)):
        base = col('#b07a45'); k = 0.85 + rng.uniform(0, 0.3)
        r = skia.Path(); r.addRRect(skia.RRect.MakeRectXY(skia.Rect(x + 8, -1400, x + 58, 600), 6, 6))
        fill(c, r, Material(shade(base, k), 'card', 0.6, light=1.15, dark=0.7, seed=120 + i % 7))
        for j in range(5):    # słoje
            yy = rng.uniform(-1300, 500)
            c.drawLine(x + 14, yy, x + 52, yy + rng.uniform(-30, 30), skia.Paint(AntiAlias=True, StrokeWidth=2, Color4f=skia.Color4f(0.3, 0.18, 0.08, 0.35)))
    card(c, (-1250, -980, -900, -880), '#3a0d0d', 14, 'card', 130, 0.5)

def set_under_back(c):
    c.drawRect(skia.Rect(-1800, -1400, 1800, 1600), skia.Paint(Color4f=col('#07070b')))
    # tył playboardu: surowa sklejka z zastrzałami
    r = _rect(-1700, -60, 1700, 60); fill(c, r, Material('#7a6a55', 'card', 0.8, seed=140))
    for x in range(-1600, 1700, 400):
        lp = skia.Paint(AntiAlias=True, StrokeWidth=26, Color4f=col('#5e5040')); c.drawLine(x, 60, x + 200, 900, lp)

SETS = {
    'kitchen': (set_kitchen_back, set_kitchen_mid), 'office': (set_office_back, set_office_mid), 'conf': (set_conf_back, set_conf_mid),
    'show': (set_show_back, set_show_riser), 'studio_g': (set_studio_g_back, set_studio_g_mid), 'road': (set_road_back, None),
    'heaven': (set_heaven_back, None), 'wood': (set_wood_back, None), 'under': (set_under_back, None), 'curtain': (None, None)}

def draw_set_layer(cv, name, layer):
    fns = SETS.get(name, (None, None))
    fn = fns[0] if layer == 'back' else fns[1]
    if fn is None: return
    cv.drawPicture(cached((name, layer), fn))
