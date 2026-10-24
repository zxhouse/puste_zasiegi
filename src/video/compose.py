"""Składanie klatki sceny z opisu (scene dict) - bez stanu, tylko z czasu t i opisu."""
import skia, math, numpy as np
import engine as E, stage as S
from puppet import col
from gfx import light_pool, beam

class Actor:
    __slots__ = ('ch', 'x', 'y', 'depth', 'scale', 'pose', 'name')
    def __init__(self, ch, x, y=0.0, depth=0.0, scale=1.0, pose=None, name=None):
        self.ch, self.x, self.y, self.depth, self.scale, self.pose, self.name = ch, x, y, depth, scale, pose or {}, name or ch.name

def _layer(cv, cam, depth, fn):
    cv.save(); cam.apply(cv, depth); fn(); cv.restore()

def opening_clip(cv, cam):
    cv.save(); cam.apply(cv, S.D_PORTAL)
    cv.clipRRect(skia.RRect.MakeRectXY(skia.Rect(S.OPEN_L, S.OPEN_T, S.OPEN_R, 470), 40, 40), doAntiAlias=True)
    cv.resetMatrix()

def draw_actor(cv, a):
    cv.save(); cv.translate(a.x, a.y); cv.scale(a.scale, a.scale)
    a.ch.draw(cv, a.pose)
    cv.restore()

def actor_shadow(cv, a, light_x, strength=0.35):
    """Miękki cień lalki rzucony na dekorację (rysowany w warstwie tła)."""
    s = a.scale*a.ch.scale
    hx = a.x + (a.x - light_x)*0.18
    p = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.05, 0.02, 0.05, strength)); p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40*s))
    top = a.y + (a.ch.head_y - a.ch.head_h*1.1)*s
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(hx - a.ch.head_w*1.05*s, top - 40, hx + a.ch.head_w*1.05*s, a.y + 100), 90*s, 90*s), p)

def render_stage(cv, sc, t):
    cam = sc['cam']
    L = sc.get('lights', {})
    amb = L.get('ambient', 1.0)
    cv.clear(skia.Color4f(0, 0, 0, 1))
    _layer(cv, cam, 600, lambda: S.studio(cv, t))
    opening_clip(cv, cam)
    # --- tło dekoracji (z przelotem z góry przy zmianie)
    for name, dy in sc.get('sets', []):
        def back(name=name, dy=dy):
            cv.translate(0, dy); S.draw_set_layer(cv, name, 'back')
            for fn in sc.get('back_props', []):
                if fn[0] == name: fn[1](cv, t)
        _layer(cv, cam, S.D_BACK, back)
    # cienie lalek na dekoracji
    lx = L.get('key_x', 0.0)
    def shadows():
        for a in sc.get('actors', []):
            if a.depth < 100: actor_shadow(cv, a, lx, 0.32*L.get('shadow', 1.0))
    _layer(cv, cam, S.D_BACK - 20, shadows)
    # oświetlenie dekoracji: przyciemnienie poza plamą światła (multiply)
    def wash():
        g = skia.GradientShader.MakeRadial(skia.Point(L.get('wash_x', 0.0), L.get('wash_y', -380)), L.get('wash_r', 1500),
                                           [skia.Color4f(*L.get('wash_col', (1.0, 0.97, 0.92)), 1).toColor(), skia.Color4f(*L.get('edge_col', (0.42, 0.38, 0.48)), 1).toColor()], [0.15, 1])
        p = skia.Paint(); p.setShader(g); p.setBlendMode(skia.BlendMode.kMultiply)
        cv.drawRect(skia.Rect(-2600, -2200, 2600, 1400), p)
        if amb < 1: cv.drawRect(skia.Rect(-2600, -2200, 2600, 1400), skia.Paint(Color4f=skia.Color4f(amb, amb, amb, 1), BlendMode=skia.BlendMode.kMultiply))
    _layer(cv, cam, S.D_BACK, wash)
    for name, dy in sc.get('sets', []):
        def mid(name=name, dy=dy):
            cv.translate(0, dy*0.7); S.draw_set_layer(cv, name, 'mid')
        _layer(cv, cam, S.D_MID, mid)
    # --- wszystko inne posortowane wg głębokości (od najdalszych): lalki, rekwizyty, światła, playboard, kurtyna, przedscenie
    items = []
    for a in sc.get('actors', []):
        items.append((a.depth, 2, lambda a=a: draw_actor(cv, a)))
        for (x, y, r, c, al) in L.get('spots', []):
            pass
    for d, f in sc.get('props', []): items.append((d, 1, lambda f=f: f(cv, t)))
    for d, f in sc.get('front_props', []): items.append((d, 1, lambda f=f: f(cv, t)))
    for d, f in sc.get('curtain_props', []): items.append((d, 1, lambda f=f: f(cv, t)))
    def spots():
        for (x, y, r, c, a) in L.get('spots', []): light_pool(cv, x, y, r, r*0.85, c, a)
        for (x0, y0, x1, y1, w0, w1, c, a) in L.get('beams', []): beam(cv, x0, y0, x1, y1, w0, w1, c, a)
    items.append((-1.0, 3, spots))
    items.append((S.D_PLAY, 0, lambda: S.playboard(cv, t)))
    if sc.get('curtain', 1.0) < 0.999:
        items.append((S.D_CURT, 0, lambda: S.curtain(cv, t, sc.get('curtain', 1.0), sc.get('curtain_sway', 0.3))))
    items.sort(key=lambda it: (-it[0], it[1]))
    for d, k, fn in items: _layer(cv, cam, d, fn)
    if L.get('dim', 0) > 0:
        cv.drawRect(skia.Rect(0, 0, E.W, E.H), skia.Paint(Color4f=skia.Color4f(0, 0, 0, L['dim'])))
    cv.restore()     # koniec przycięcia do otworu sceny
    P = sc.get('portal', {})
    _layer(cv, cam, S.D_PORTAL, lambda: S.portal(cv, t, P.get('chase', 0.0), P.get('bulbs', 1.0), P.get('marquee')))
    _layer(cv, cam, S.D_TRUSS, lambda: S.truss(cv, t))
    for d, f in sc.get('fg', []): _layer(cv, cam, d, lambda f=f: f(cv, t))
    if L.get('flash', 0) > 0.003:
        cv.drawRect(skia.Rect(0, 0, E.W, E.H), skia.Paint(Color4f=skia.Color4f(1, 0.98, 0.92, min(L['flash'], 0.85)), BlendMode=skia.BlendMode.kPlus))
