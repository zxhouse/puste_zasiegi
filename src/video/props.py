"""Rekwizyty (tektura, filc, sklejka) - funkcje rysujące w układzie lokalnym (0,0 = punkt zaczepienia)."""
import skia, math, numpy as np
from puppet import Material, fill, poly_path, col, shade, fur_fringe
from gfx import card, draw_text, text_width, light_pool, drop_shadow
import engine as E

GRIP = 95          # tabliczka zaczyna się tyle px nad dłonią; drążek przechodzi przez pięść i wystaje pod nią
STICK_BELOW = 120
def _stick(cv, w=9, top=-GRIP, color='#a0743f'):
    """Drążek trzymany w pięści (0,0 = środek dłoni): od spodu tabliczki przez dłoń w dół."""
    p = skia.Paint(AntiAlias=True, StrokeWidth=w, Color4f=col(color), StrokeCap=skia.Paint.kRound_Cap)
    cv.drawLine(0, top, 0, STICK_BELOW, p)
    hl = skia.Paint(AntiAlias=True, StrokeWidth=w*0.3, Color4f=skia.Color4f(1, 0.9, 0.7, 0.35)); cv.drawLine(-w*0.2, top, -w*0.2, STICK_BELOW, hl)

def mug(cv, color='#e05d5d', steam=0.0, t=0.0):
    card(cv, (-34, -70, 34, 10), color, 12, 'card', 201, 0.6)
    cv.drawArc(skia.Rect(22, -58, 62, -10), -90, 180, False, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=10, Color4f=col(color)))
    draw_text(cv, '☕', 0, -18, 'hand', 1, color)
    if steam > 0:
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=skia.Color4f(1, 1, 1, 0.55*steam), StrokeCap=skia.Paint.kRound_Cap)
        for k in (-14, 6):
            path = skia.Path(); path.moveTo(k, -78)
            for j in range(1, 6): path.lineTo(k + 9*math.sin(t*6 + j + k), -78 - j*16)
            cv.drawPath(path, p)

def hanger_jacket(cv, color='#6f7480'):
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color4f=col('#dddddd'))
    cv.drawLine(-60, -1400, -60, -20, p); cv.drawLine(60, -1400, 60, -20, p)      # sznurki
    hp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=7, Color4f=col('#8b5a2b'))
    cv.drawLine(-110, 0, 0, -40, hp); cv.drawLine(110, 0, 0, -40, hp); cv.drawLine(-110, 0, 110, 0, hp)
    body = [(-120, 0), (-130, 220), (130, 220), (120, 0), (40, -10), (0, 60), (-40, -10)]
    fill(cv, poly_path(body, True, True), Material(color, 'felt', 0.7, seed=202))
    for sg in (-1, 1):
        L = [(sg*40, -8), (sg*80, 6), (sg*30, 110), (sg*5, 70)]
        fill(cv, poly_path(L, True, False), Material(shade(col(color), 0.8), 'felt', 0.7, seed=203))

def apple_logo(r):
    """Ścieżka logo z nadgryzionym jabłkiem (wysokość ~2r, środek w 0,0)."""
    U = lambda p, q: skia.Op(p, q, skia.PathOp.kUnion_PathOp); D = lambda p, q: skia.Op(p, q, skia.PathOp.kDifference_PathOp)
    body = U(skia.Path().addOval(skia.Rect(-r*0.95, -r*0.58, r*0.12, r*0.98)), skia.Path().addOval(skia.Rect(-r*0.12, -r*0.58, r*0.95, r*0.98)))
    body = U(body, skia.Path().addOval(skia.Rect(-r*0.62, -r*0.66, r*0.62, r*0.9)))
    body = D(body, skia.Path().addCircle(0, -r*0.68, r*0.14))
    body = D(body, skia.Path().addCircle(0, r*1.04, r*0.13))
    body = D(body, skia.Path().addCircle(r*1.05, -r*0.02, r*0.33))
    leaf = skia.Path().addOval(skia.Rect(-r*0.13, -r*0.26, r*0.13, r*0.26)); leaf.transform(skia.Matrix.RotateDeg(38)); leaf.offset(r*0.16, -r*0.98)
    return U(body, leaf)
def laptop(cv, glow=0.6, t=0.0):
    """MacBook widziany od tyłu (v6): ekran zwrócony do piszącego Henia, do kamery tył aluminiowej klapy z podświetlonym
    logo jabłka; od spodu klapy cienka krawędź korpusu; niebieskawy blask ekranu na twarzy Henia (za klapą)."""
    light_pool(cv, 0, -250, 260, 170, (0.62, 0.78, 1.0), 0.22*glow)
    lid = skia.Path(); lid.addRRect(skia.RRect.MakeRectXY(skia.Rect(-170, -200, 170, 14), 14, 14))
    g = skia.GradientShader.MakeLinear([skia.Point(-170, -200), skia.Point(170, 14)], [col('#e6e8eb').toColor(), col('#b9bec5').toColor(), col('#d4d7db').toColor()], [0, 0.6, 1])
    p = skia.Paint(AntiAlias=True); p.setShader(g); cv.drawPath(lid, p)
    cv.drawPath(lid, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color4f=col('#8f949b')))
    cv.save(); cv.translate(0, -96)
    lg = apple_logo(30)
    gp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.55*glow)); gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
    cv.drawPath(lg, gp); cv.drawPath(lg, skia.Paint(AntiAlias=True, Color4f=col('#fbfcff')))
    cv.restore()
    base = skia.Path(); base.addRRect(skia.RRect.MakeRectXY(skia.Rect(-182, 12, 182, 30), 8, 8))
    gb = skia.GradientShader.MakeLinear([skia.Point(0, 12), skia.Point(0, 30)], [col('#cfd3d8').toColor(), col('#8a9097').toColor()])
    pb = skia.Paint(AntiAlias=True); pb.setShader(gb); cv.drawPath(base, pb)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-40, 12, 40, 16), 2, 2), skia.Paint(AntiAlias=True, Color4f=col('#7b8087')))

def linkedin_card(cv, text, w=520, h=230, author='Henio Kawka', smile=True, color='#ffffff', reveal=1.0, side=1):
    """Plansza 'post' z tektury: wygląda jak karta wpisu (awatar-kółko, nazwisko, tekst, pasek reakcji).
    side=+1: karta wysunięta w prawo od dłoni (żeby nie zasłaniać twarzy), -1 w lewo."""
    _stick(cv, 10)
    cv.translate(side*(w/2 - 40), -GRIP)
    path = card(cv, (-w/2, -h, w/2, 0), color, 16, 'card', 210, 0.75)
    cv.drawCircle(-w/2 + 46, -h + 46, 26, skia.Paint(AntiAlias=True, Color4f=col('#0a66c2')))
    draw_text(cv, author, -w/2 + 86, -h + 44, 'ui_b', 26, '#191919', 'left', maxw=w - 110)
    draw_text(cv, '1 godz. • 🌐'.replace('🌐', ''), -w/2 + 86, -h + 70, 'ui', 18, '#666666', 'left')
    words = text.split(); n = max(1, int(round(len(words)*reveal)))
    draw_text(cv, ' '.join(words[:n]), -w/2 + 24, -h + 130, 'ui_b', 34, '#191919', 'left', maxw=w - 48)
    cv.drawLine(-w/2 + 20, -48, w/2 - 20, -48, skia.Paint(AntiAlias=True, StrokeWidth=2, Color4f=col('#dddddd')))
    for i, c in enumerate(['#378fe9', '#44712e', '#df704d']):
        cv.drawCircle(-w/2 + 34 + i*22, -24, 12, skia.Paint(AntiAlias=True, Color4f=col(c)))
    draw_text(cv, '1 482', -w/2 + 104, -16, 'ui', 20, '#666666', 'left')

def placard(cv, text, w=None, size=46, fname='hand', color='#fff8e1', ink='#2b2b2b', stick=True, h=None, side=0):
    tw = text_width(text, fname, size); w = w or tw + 70; h = h or size*2.0
    if stick:
        _stick(cv, 10); cv.translate(0, -GRIP)
    if side: cv.translate(side*(w/2 - 30), 0)
    card(cv, (-w/2, -h, w/2, 0), color, 12, 'card', 211, 0.7, wobble=2)
    draw_text(cv, text, 0, -h/2 + size*0.35, fname, size, ink, maxw=w - 40)

def bubble(cv, text, w=None, size=40, fname='hand', tail=(-1, 1), color='#ffffff', ink='#222222', words=None):
    """Dymek komiksowy z tektury. words: liczba widocznych słów (pojawianie słowo po słowie)."""
    tw = text_width(text, fname, size); w = w or tw + 80; h = size*2.1
    pts = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (tail[0]*w*0.15 + 30*tail[0], h/2), (tail[0]*w*0.42, h/2 + 70*tail[1]), (tail[0]*w*0.05, h/2), (-w/2, h/2)]
    pp = skia.Path(); pp.addRRect(skia.RRect.MakeRectXY(skia.Rect(-w/2, -h/2, w/2, h/2), h/2, h/2))
    tp = poly_path([(tail[0]*w*0.08, h/2 - 4), (tail[0]*w*0.36, h/2 + 64), (tail[0]*w*0.24, h/2 - 4)], True, False)
    pp.addPath(tp)
    drop_shadow(cv, pp, 8, 10, 10, 0.3)
    fill(cv, pp, Material(color, 'card', 0.8, light=1.05, dark=0.9, seed=212))
    cv.drawPath(pp, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=col('#333333')))
    if words is not None:
        ws = text.split(); text = ' '.join(ws[:words])
    draw_text(cv, text, -tw/2, size*0.35, fname, size, ink, 'left')

def cloud(cv, scale=1.0, dark=0.0, lightning=0.0):
    c = shade(col('#f4f6fa'), 1 - 0.45*dark)
    for (x, y, r) in [(-70, 0, 55), (-20, -30, 66), (45, -20, 60), (85, 8, 45), (0, 22, 55), (-100, 22, 38)]:
        cv.drawCircle(x*scale, y*scale, r*scale, skia.Paint(AntiAlias=True, Color4f=c))
    fur_fringe(cv, [(-150*scale, 30*scale), (-110*scale, -50*scale), (0, -95*scale), (100*scale, -60*scale), (140*scale, 30*scale)], c, 12, 0.5, 9, 0.8, 2.0)
    if lightning > 0.05:
        pts = [(0, 60), (-25, 120), (5, 120), (-20, 190), (40, 105), (10, 105), (25, 60)]
        cv.drawPath(poly_path([(x*scale, y*scale) for x, y in pts], True, False), skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 0.9, 0.2, lightning)))

def banner(cv, text, w=900, color='#d62839', ink='#ffd166'):
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color4f=col('#dddddd'))
    cv.drawLine(-w/2 + 40, -1500, -w/2 + 40, -60, p); cv.drawLine(w/2 - 40, -1500, w/2 - 40, -60, p)
    card(cv, (-w/2, -150, w/2, 0), color, 10, 'card', 214, 0.6)
    for i in range(12):    # proporczyki
        x = -w/2 + 30 + i*(w - 60)/11
        cv.drawPath(poly_path([(x - 26, 0), (x + 26, 0), (x, 46)], True, False), skia.Paint(AntiAlias=True, Color4f=col(['#ffd166', '#06d6a0', '#118ab2'][i % 3])))
    draw_text(cv, text, 0, -45, 'block', 110, ink, stroke=('#7a1020', 8), maxw=w - 80)

def flash_bulb(cv, a):
    if a > 0.01: light_pool(cv, 0, 0, 500, 400, (1, 1, 1), 0.9*a)

def reaction_paddle(cv, kind, size=1.0):
    """Reakcja z serwisu na patyku: tekturowy krążek z białym rantem, na nim ta sama ikona co w klonie (reactions.py)."""
    import reactions as RX
    _stick(cv, 8*size, -GRIP*size); cv.translate(0, -GRIP*size)
    cy = -48*size
    sh = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.25)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4*size))
    cv.drawCircle(3*size, cy + 4*size, 54*size, sh)
    cv.drawCircle(0, cy, 54*size, skia.Paint(AntiAlias=True, Color4f=col('#f7f4ee')))
    RX.draw(cv, kind, 0, cy, 49*size)
    cv.drawCircle(0, cy, 54*size, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2*size, Color4f=col('#cfc8bb')))

def balloon_heart(cv, popped=0.0, t=0.0):
    cv.drawLine(0, 0, 0, 260, skia.Paint(AntiAlias=True, StrokeWidth=3, Color4f=col('#888888')))
    if popped < 0.05:
        cv.save(); cv.translate(0, -90); cv.rotate(4*math.sin(t*2))
        hp = poly_path([(0, 70), (-80, 0), (-75, -55), (-35, -75), (0, -45), (35, -75), (75, -55), (80, 0)], True, True)
        g = skia.GradientShader.MakeRadial(skia.Point(-25, -40), 120, [col('#ff8fa3').toColor(), col('#e63946').toColor(), col('#9d0208').toColor()], [0, 0.5, 1])
        p = skia.Paint(AntiAlias=True); p.setShader(g); cv.drawPath(hp, p); cv.restore()
    else:
        rng = np.random.default_rng(3)
        for k in range(10):
            a = k*0.63; d = 40 + 160*popped
            cv.save(); cv.translate(d*math.cos(a), -90 + d*math.sin(a) + 80*popped**2); cv.rotate(a*60 + popped*200)
            cv.drawRect(skia.Rect(-14, -6, 14, 6), skia.Paint(AntiAlias=True, Color4f=col('#e63946', max(0, 1 - popped))))
            cv.restore()
        if popped < 0.4: draw_text(cv, 'PĘK!', 0, -60, 'block', 90, '#ffd166', stroke=('#9d0208', 8), alpha=1 - popped/0.4)

def comic_panel(cv, kind, w=220, h=170):
    card(cv, (-w/2, -h, w/2, 0), '#fffdf5', 6, 'card', 220, 0.6)
    cv.drawRect(skia.Rect(-w/2 + 10, -h + 10, w/2 - 10, -10), skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=col('#222222')))
    ink = skia.Paint(AntiAlias=True, Color4f=col('#222222'))
    if kind == 0:   # wschód słońca
        cv.drawCircle(0, -40, 46, skia.Paint(AntiAlias=True, Color4f=col('#ffb703'))); cv.drawRect(skia.Rect(-w/2 + 12, -40, w/2 - 12, -12), skia.Paint(Color4f=col('#219ebc')))
    elif kind == 1:  # kawa
        mug(cv, '#8d6e63')
    elif kind == 2:  # siłownia (hantel)
        cv.drawRect(skia.Rect(-60, -92, 60, -80), ink); cv.drawRect(skia.Rect(-80, -112, -60, -60), ink); cv.drawRect(skia.Rect(60, -112, 80, -60), ink)
    elif kind == 3:  # pies
        cv.drawCircle(0, -80, 34, skia.Paint(AntiAlias=True, Color4f=col('#a1887f'))); cv.drawCircle(-30, -100, 14, ink); cv.drawCircle(30, -100, 14, ink); cv.drawCircle(0, -70, 8, ink)
    else:            # medal
        cv.drawCircle(0, -70, 40, skia.Paint(AntiAlias=True, Color4f=col('#ffd166'))); draw_text(cv, '1', 0, -52, 'block', 50, '#7a5c12')

def scroll(cv, length, text='#wdzięczność'):
    card(cv, (-150, -20, 150, 20), '#d4a373', 20, 'card', 230, 0.6)
    card(cv, (-130, 0, 130, length), '#fbf3e4', 2, 'card', 231, 0.5)
    n = int(length//52)
    for i in range(n):
        y = 46 + i*52
        cv.drawLine(-110, y - 22, 110, y - 22, skia.Paint(AntiAlias=True, StrokeWidth=2, Color4f=col('#e0d4bd')))
        draw_text(cv, text, 0, y, 'script', 34, '#d63384', maxw=220)

def box_of_stuff(cv):
    card(cv, (-110, -110, 110, 0), '#c8a165', 6, 'card', 240, 0.6)
    cv.drawLine(-110, -80, 110, -80, skia.Paint(AntiAlias=True, StrokeWidth=3, Color4f=col('#8a6a3a')))
    for (x, h, c) in [(-60, 80, '#2d6a4f'), (-10, 50, '#e63946'), (50, 70, '#457b9d')]:
        card(cv, (x - 18, -110 - h, x + 18, -100), c, 6, 'card', 241, 0.6)
    fur_fringe(cv, [(-80, -190), (-60, -215), (-40, -190)], col('#52b788'), 30, 1.2, 5, 0.6, 5)

def stamp(cv, down=0.0):
    """Pieczątka trzymana jak prawdziwa: pięść na toczonej rączce, gałka nad pięścią, pod nią drewniany klocek
    i czerwona guma z (lustrzanym) napisem - pieczątka zwisa pionowo pod dłonią."""
    cv.drawCircle(0, -46, 30, skia.Paint(AntiAlias=True, Color4f=col('#3a2416')))                       # gałka
    cv.drawCircle(-9, -55, 9, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.25)))
    hp = skia.Path(); hp.addRRect(skia.RRect.MakeRectXY(skia.Rect(-17, -30, 17, 96), 12, 12))
    fill(cv, hp, Material('#8b5a2b', 'card', 0.8, light=1.2, dark=0.75, seed=251))                        # rączka
    card(cv, (-36, 86, 36, 104), '#5b3820', 4, 'card', 253, 0.6)                                          # kołnierz
    card(cv, (-112, 100, 112, 158), '#6b4226', 8, 'card', 250, 0.6)                                        # klocek
    card(cv, (-118, 156, 118, 178), '#c1121f', 4, 'card', 252, 0.6)                                        # guma

def stamp_mark(cv, a):
    if a <= 0.01: return
    cv.save(); cv.rotate(-12)
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8, Color4f=col('#c1121f', a))
    tw = text_width('RESTRUKTURYZACJA', 'block', 60)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-tw/2 - 34, -66, tw/2 + 34, 34), 12, 12), p)
    draw_text(cv, 'RESTRUKTURYZACJA', 0, 4, 'block', 60, '#c1121f', alpha=a)
    cv.restore()

def cobble(cv, k=0):
    """Kostka bruku w garści: nieregularny granitowy kamień (cieniowanie z góry-lewej, ziarno, krawędzie)."""
    rng = np.random.default_rng(260 + k)
    n = 9; ang = np.linspace(0, 2*np.pi, n, endpoint=False) + rng.uniform(-0.15, 0.15, n)
    rx, ry = 58 + rng.uniform(-6, 6), 46 + rng.uniform(-5, 5)
    pts = [(rx*math.cos(a)*(0.88 + 0.12*abs(math.cos(a))) + rng.uniform(-4, 4), -38 + ry*math.sin(a)*(0.9 + 0.1*abs(math.sin(a))) + rng.uniform(-4, 4)) for a in ang]
    path = poly_path(pts, True, True)
    base = ['#8d8a84', '#7e7a74', '#96918a'][k % 3]
    g = skia.GradientShader.MakeRadial(skia.Point(-22, -62), 120, [shade(col(base), 1.35).toColor(), col(base).toColor(), shade(col(base), 0.55).toColor()], [0, 0.45, 1])
    pp = skia.Paint(AntiAlias=True); pp.setShader(g); cv.drawPath(path, pp)
    cv.save(); cv.clipPath(path, doAntiAlias=True)
    for j in range(70):
        x, y = rng.uniform(-60, 60), rng.uniform(-90, 10)
        cv.drawCircle(x, y, rng.uniform(1, 2.6), skia.Paint(AntiAlias=True, Color4f=skia.Color4f(*([0.2]*3 if j % 2 else [0.92]*3), 0.35)))
    cv.restore()
    cv.drawPath(path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color4f=skia.Color4f(0.2, 0.19, 0.18, 0.6)))

def flipchart(cv, page=0):
    lp = skia.Paint(AntiAlias=True, StrokeWidth=12, Color4f=col('#555555'))
    cv.drawLine(-160, 0, -120, -560, lp); cv.drawLine(160, 0, 120, -560, lp)
    card(cv, (-200, -620, 200, -200), '#ffffff', 6, 'card', 270, 0.6)
    draw_text(cv, 'MOJE ŻYCIE:', 0, -555, 'hand', 44, '#1b2f5e', maxw=340); draw_text(cv, 'CASE STUDY', 0, -505, 'block', 50, '#e0563b', maxw=340)
    cx, cy, r = 0, -340, 105
    vals = [0.45, 0.25, 0.2, 0.1]; cols = ['#e0563b', '#1b2f5e', '#f2b48a', '#9ad9b5']; a = -90
    for v, c in zip(vals, cols):
        cv.drawArc(skia.Rect(cx - r, cy - r, cx + r, cy + r), a, v*360, True, skia.Paint(AntiAlias=True, Color4f=col(c))); a += v*360

def star_shape(cv, x, y, r, color):
    pts = [(x + (r if k % 2 == 0 else r*0.45)*math.cos(-math.pi/2 + k*math.pi/5), y + (r if k % 2 == 0 else r*0.45)*math.sin(-math.pi/2 + k*math.pi/5)) for k in range(10)]
    cv.drawPath(poly_path(pts, True, False), skia.Paint(AntiAlias=True, Color4f=col(color)))
def star_card(cv, n=1):
    _stick(cv, 8); cv.translate(0, -GRIP)
    card(cv, (-70, -120, 70, 0), '#fff3b0', 10, 'card', 280, 0.6)
    star_shape(cv, 0, -60, 48, '#f4a261')

def price_tag(cv):
    _stick(cv, 8); cv.translate(0, -GRIP*0.8)
    card(cv, (-90, -60, 90, 0), '#ffe066', 8, 'card', 285, 0.6)
    draw_text(cv, '3 OPINIE', 0, -18, 'block2', 34, '#3a3a3a')

def halo(cv, glow=1.0):
    cv.drawLine(0, 0, 0, -900, skia.Paint(AntiAlias=True, StrokeWidth=2.5, Color4f=col('#dddddd')))
    light_pool(cv, 0, 30, 220, 80, (1.0, 0.85, 0.4), 0.45*glow)
    cv.save(); cv.scale(1, 0.32)
    cv.drawCircle(0, 90, 120, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=34, Color4f=col('#f2c94c')))
    cv.drawCircle(0, 90, 120, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=10, Color4f=col('#fff3b0')))
    cv.restore()

def smile_mask(cv, crack=0.0):
    _stick(cv, 8, -GRIP + 20); cv.translate(0, -GRIP + 20)
    cv.drawCircle(0, -70, 70, skia.Paint(AntiAlias=True, Color4f=col('#fff1c1')))
    cv.drawCircle(0, -70, 70, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=col('#c9a227')))
    ink = skia.Paint(AntiAlias=True, Color4f=col('#222222'))
    cv.drawCircle(-24, -92, 8, ink); cv.drawCircle(24, -92, 8, ink)
    cv.drawArc(skia.Rect(-45, -105, 45, -30), 20, 140, False, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=7, Color4f=col('#222222'), StrokeCap=skia.Paint.kRound_Cap))
    if crack > 0.01:
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4, Color4f=col('#3a2a1a'))
        pts = [(-10, -140), (5, -110), (-12, -85), (10, -60), (-5, -30), (12, -2)]
        n = 1 + int(crack*5)
        path = skia.Path(); path.moveTo(*pts[0])
        for q in pts[1:n + 1]: path.lineTo(*q)
        cv.drawPath(path, p)

def podcast_mic(cv):
    lp = skia.Paint(AntiAlias=True, StrokeWidth=12, Color4f=col('#333333'), StrokeCap=skia.Paint.kRound_Cap)
    cv.drawLine(-400, -600, -120, -420, lp); cv.drawLine(-120, -420, -60, -340, lp)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-90, -400, -20, -260), 30, 30), skia.Paint(AntiAlias=True, Color4f=col('#1d1d1d')))
    for k in range(5): cv.drawLine(-86, -380 + k*24, -24, -380 + k*24, skia.Paint(AntiAlias=True, StrokeWidth=2, Color4f=col('#555555')))

def on_air(cv, on):
    card(cv, (-170, -60, 170, 60), '#2a0b0b', 12, 'card', 290, 0.5)
    draw_text(cv, 'ON AIR', 0, 25, 'block', 70, '#ff3b30' if on > 0.5 else '#5a1e1e')
    if on > 0.5: light_pool(cv, 0, 0, 300, 140, (1, 0.2, 0.15), 0.35)

def marker_sign(cv, text, reveal=1.0, w=520, h=260):
    cv.drawLine(0, -h, 0, -1500, skia.Paint(AntiAlias=True, StrokeWidth=2.5, Color4f=col('#dddddd')))
    card(cv, (-w/2, -h, w/2, 0), '#c9a26b', 4, 'card', 300, 0.55, wobble=3)
    words = text.split(); n = int(math.floor(len(words)*reveal + 1e-6))
    draw_text(cv, ' '.join(words[:n]), 0, -h/2 + 22, 'hand', 70, '#1a1a1a', maxw=w - 60)

def ornament(cv, k=0, t=0.0):
    c = ['#ffd166', '#ef476f', '#06d6a0', '#118ab2'][k % 4]
    cv.save(); cv.rotate(30*math.sin(t*3 + k))
    pts = [(math.cos(a)*(30 if i % 2 == 0 else 13), math.sin(a)*(30 if i % 2 == 0 else 13)) for i, a in enumerate(np.linspace(0, 2*np.pi, 11)[:-1] - np.pi/2)]
    cv.drawPath(poly_path(pts, True, False), skia.Paint(AntiAlias=True, Color4f=col(c)))
    cv.restore()

def trumpet(cv):
    g = skia.Paint(AntiAlias=True, Color4f=col('#e9c46a'))
    cv.drawPath(poly_path([(-20, 0), (-12, -260), (-70, -360), (70, -360), (12, -260), (20, 0)], True, True), g)
    cv.drawOval(skia.Rect(-70, -380, 70, -340), skia.Paint(AntiAlias=True, Color4f=col('#b08a2e')))

def tear(cv):
    _stick(cv, 8); cv.translate(0, -GRIP + 10)
    cv.drawPath(poly_path([(0, -170), (40, -70), (30, -30), (0, -10), (-30, -30), (-40, -70)], True, True), skia.Paint(AntiAlias=True, Color4f=col('#74c0fc')))

def confetti(cv, t, t0, n=160, area=(-1100, 1100), seed=4):
    if t < t0: return
    rng = np.random.default_rng(seed)
    for k in range(n):
        x0 = rng.uniform(*area); v = rng.uniform(180, 320); ph = rng.uniform(0, 6.28); c = ['#ffd166', '#ef476f', '#06d6a0', '#118ab2', '#f78c6b', '#ffffff'][k % 6]
        delay = rng.uniform(0, 1.2)
        tt = t - t0 - delay
        if tt < 0: continue
        y = -1000 + v*tt
        if y > 500: continue
        x = x0 + 40*math.sin(tt*2 + ph)
        cv.save(); cv.translate(x, y); cv.rotate(tt*200 + ph*50); cv.scale(1, abs(math.cos(tt*5 + ph)) + 0.15)
        cv.drawRect(skia.Rect(-10, -6, 10, 6), skia.Paint(AntiAlias=True, Color4f=col(c)))
        cv.restore()

def phone(cv, screen='#0a66c2', t=0.0, scroll=0.0):
    """Smartfon z mobilnym feedem serwisu (v6): pasek stanu, nagłówek z awatarem i wyszukiwarką, karty wpisów (awatar, nazwisko,
    tekst, zdjęcie, reakcje - te same ikony co w klonie, przyciski), dolna nawigacja; feed przewija się (scroll w px ekranu)."""
    import reactions as RX
    card(cv, (-62, -124, 62, 124), '#1c1c1e', 20, 'card', 310, 0.5)
    scr = skia.Rect(-53, -112, 53, 112)
    cv.save(); cv.clipRRect(skia.RRect.MakeRectXY(scr, 9, 9), doAntiAlias=True)
    cv.drawRect(scr, skia.Paint(Color4f=col('#f4f2ee')))
    W = skia.Paint(AntiAlias=True, Color4f=col('#ffffff')); G = skia.Paint(AntiAlias=True, Color4f=col('#d5d3cf'))
    G2 = skia.Paint(AntiAlias=True, Color4f=col('#9b9894')); B = skia.Paint(AntiAlias=True, Color4f=col('#0a66c2'))
    pics = ['#7a3db8', '#e9c46a', '#5aa9e6', '#e07a5f', '#73b7a6']; avs = ['#d6b48c', '#f2a1c0', '#8e3f4a', '#a4c3f0', '#ffd166']
    y = -84 - (scroll % 150)
    k0 = int(scroll // 150)
    for k in range(k0, k0 + 3):
        cv.drawRect(skia.Rect(-53, y, 53, y + 144), W)
        cv.drawCircle(-41, y + 11, 7, skia.Paint(AntiAlias=True, Color4f=col(avs[k % 5])))
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-30, y + 6, 8 + (k*13) % 20, y + 10), 2, 2), G2)
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-30, y + 13, -2, y + 16), 1.5, 1.5), G)
        for j in range(2): cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-48, y + 23 + j*7, 46 - j*30 - (k*9) % 14, y + 27 + j*7), 2, 2), G)
        cv.drawRect(skia.Rect(-53, y + 40, 53, y + 108), skia.Paint(Color4f=col(pics[k % 5])))
        cv.drawCircle(-14 + (k*17) % 30, y + 72, 14, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.35)))
        for i, rk in enumerate(['like', 'heart', 'clap'][:2 + k % 2]): RX.draw(cv, rk, -45 + i*6, y + 116, 3.6)
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-30, y + 114, -14, y + 118), 2, 2), G)
        cv.drawLine(-48, y + 124, 48, y + 124, skia.Paint(StrokeWidth=0.8, Color4f=col('#e3e1dd')))
        for i in range(4): cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-46 + i*25, y + 130, -34 + i*25, y + 136), 2, 2), G)
        y += 150
    cv.drawRect(skia.Rect(-53, -112, 53, -78), W)                                         # nagłówek
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-26, -100, 30, -86), 7, 7), skia.Paint(AntiAlias=True, Color4f=col('#edf3f8')))
    cv.drawCircle(-41, -93, 7, skia.Paint(AntiAlias=True, Color4f=col('#d6b48c')))
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(36, -99, 48, -88), 2, 2), G2)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-14, -110, 14, -106), 2, 2), skia.Paint(AntiAlias=True, Color4f=col('#1c1c1e')))   # wycięcie aparatu
    cv.drawRect(skia.Rect(-53, 92, 53, 112), W)                                           # dolna nawigacja
    for i in range(5):
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-47 + i*20, 96, -39 + i*20, 104), 2, 2), B if i == 0 else G2)
    cv.restore()
    gl = skia.Paint(AntiAlias=True); gl.setShader(skia.GradientShader.MakeLinear([skia.Point(-60, -120), skia.Point(60, 40)],
                                       [skia.Color4f(1, 1, 1, 0.18).toColor(), skia.Color4f(1, 1, 1, 0).toColor()]))
    cv.drawRRect(skia.RRect.MakeRectXY(scr, 9, 9), gl)                                     # odblask szyby

def desk_mic(cv):
    """Mikrofon podcastowy na krótkim statywie stojący na krawędzi sceny."""
    lp = skia.Paint(AntiAlias=True, StrokeWidth=12, Color4f=col('#2a2a2a'), StrokeCap=skia.Paint.kRound_Cap)
    cv.drawLine(0, 0, 0, -150, lp); cv.drawLine(-60, 0, 60, 0, lp)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-34, -300, 34, -150), 30, 30), skia.Paint(AntiAlias=True, Color4f=col('#1d1d1d')))
    for k in range(5): cv.drawLine(-30, -280 + k*24, 30, -280 + k*24, skia.Paint(AntiAlias=True, StrokeWidth=2, Color4f=col('#555555')))
    cv.drawCircle(0, -225, 60, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6, Color4f=col('#3a3a3a')))

def podcast_desk(cv, seats):
    """Stół podcastowy z jasnego drewna (zasłania lalki do pasa) + mikrofony na ramionach przy każdym miejscu.
    seats: lista (x, y_ust, strona_mikrofonu, skala) - mikrofon z boku ust, nie zasłania ruchu szczęki."""
    top = -105
    body = skia.Path(); body.addRRect(skia.RRect.MakeRectXY(skia.Rect(-1080, top + 14, 1080, 120), 18, 18))
    fill(cv, body, Material('#9b6a3f', 'card', 0.8, light=1.12, dark=0.78, seed=410))
    for k in range(7):     # słoje
        y = top + 34 + k*14
        cv.drawLine(-1060, y, 1060, y + 4*math.sin(k), skia.Paint(AntiAlias=True, StrokeWidth=2, Color4f=skia.Color4f(0.3, 0.17, 0.07, 0.22)))
    blat = skia.Path(); blat.addRRect(skia.RRect.MakeRectXY(skia.Rect(-1100, top - 10, 1100, top + 16), 10, 10))
    fill(cv, blat, Material('#c38f5c', 'card', 0.8, light=1.15, dark=0.85, seed=411))
    arm = skia.Paint(AntiAlias=True, StrokeWidth=11, Color4f=col('#1c1c1e'), StrokeCap=skia.Paint.kRound_Cap)
    for (x, my, side, k) in seats:
        bx = x + side*250*k; mx = x + side*158*k; mcy = my + 62*k
        jx, jy = (bx + mx)/2 + side*30*k, top - 170*k
        cv.drawRect(skia.Rect(bx - 16, top - 22, bx + 16, top + 8), skia.Paint(Color4f=col('#2a2a2c')))
        cv.drawLine(bx, top - 12, jx, jy, arm); cv.drawLine(jx, jy, mx + side*30*k, mcy - 40*k, arm)
        cv.save(); cv.translate(mx, mcy); cv.scale(k, k); cv.rotate(-side*14)
        cv.drawCircle(0, 0, 50, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=col('#3a3a3c')))
        cap = skia.Path(); cap.addRRect(skia.RRect.MakeRectXY(skia.Rect(-26, -62, 26, 54), 24, 24))
        fill(cv, cap, Material('#2c2c31', 'felt', 0.6, light=1.3, dark=0.7, seed=412))
        for j in range(5): cv.drawLine(-22, -44 + j*16, 22, -44 + j*16, skia.Paint(AntiAlias=True, StrokeWidth=2, Color4f=col('#55555c')))
        cv.restore()
    # kubki na stole
    for x in (-250, 300):
        cv.save(); cv.translate(x, top + 4); cv.scale(0.8, 0.8); mug(cv, '#e9e3d5'); cv.restore()

def rec_card(cv, k=0):
    """Rekomendacja z serwisu na patyku: awatar, imię, cytat - 'trzy opinie'."""
    _stick(cv, 8); cv.translate(0, -GRIP)
    card(cv, (-120, -150, 120, 0), '#ffffff', 14, 'card', 280 + k, 0.55, light=1.04, dark=0.95)
    av = ['#f2c14e', '#6cbf84', '#e07a5f'][k % 3]
    cv.drawCircle(-82, -112, 24, skia.Paint(AntiAlias=True, Color4f=col(av)))
    for ex in (-90, -74): cv.drawCircle(ex, -116, 5, skia.Paint(AntiAlias=True, Color4f=col('#ffffff')))
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-50, -126, 70, -112), 6, 6), skia.Paint(AntiAlias=True, Color4f=col('#3c3c3c')))
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-50, -104, 30, -94), 5, 5), skia.Paint(AntiAlias=True, Color4f=col('#b8b8b8')))
    draw_text(cv, '„', -96, -38, 'ui_b', 64, '#0a66c2')
    draw_text(cv, ['Wizjoner!', 'Szacun!', 'Polecam!'][k % 3], 14, -36, 'ui_b', 30, '#222222', maxw=150)

def rec_tag(cv):
    """Metka 'na sprzedaż': cena = 3 rekomendacje (z ikonką serwisu)."""
    _stick(cv, 8); cv.translate(0, -GRIP*0.8)
    pth = poly_path([(-120, -86), (90, -86), (126, -43), (90, 0), (-120, 0)], True, False)
    fill(cv, pth, Material('#ffe066', 'card', 0.8, light=1.08, dark=0.9, seed=285))
    cv.drawPath(pth, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.5, Color4f=col('#b8901c')))
    cv.drawCircle(96, -43, 9, skia.Paint(AntiAlias=True, Color4f=col('#7a5c12')))
    draw_text(cv, 'CENA:', -16, -54, 'block2', 22, '#3a3a3a')
    draw_text(cv, '3 rekomendacje', -16, -18, 'ui_b', 26, '#0a66c2', maxw=196)
