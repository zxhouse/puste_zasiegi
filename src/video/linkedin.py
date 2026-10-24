"""Przebitki do klonu serwisu: zrzuty strony (build/clone_caps, Playwright) + film ze sceny w ramce posta +
liczniki/pisanie słowo po słowie (czasy z dopasowania) + kursor. Wszystko liczone z czasu t (bezstanowo)."""
import json, os, math, numpy as np, skia
import engine as E, timeline as T, compose as CP
from engine import smoothstep, Cam
from signs import _tokens
from gfx import font, text_width, light_pool
CAPS = os.path.join(E.ROOT, 'build', 'clone_caps')
META = json.load(open(os.path.join(CAPS, 'meta.json')))
_IM = {}
def img(name):
    if name not in _IM:
        if len(_IM) > 8: _IM.pop(next(iter(_IM)))
        _IM[name] = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(os.path.join(CAPS, name)))
    return _IM[name]
def R(state, key): return META[state]['rects'].get(key)

# ------------------------------------------------------------------ formaty liczb i odmiana
def fmt(n): return f'{int(n):,}'.replace(',', ' ')
def plural(n, one, few, many):
    n = int(n)
    if n == 1: return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14: return few
    return many

# ------------------------------------------------------------------ kamera na ekranie przeglądarki
def interp_view(a, b, u):
    """a, b = (sy, cx, cy, w). Zbliżenie 'prosto do celu': szerokość geometrycznie, środek proporcjonalnie."""
    u = smoothstep(u)
    sy = a[0] + (b[0] - a[0])*u
    w = a[3]*(b[3]/a[3])**u
    k = (a[3] - w)/(a[3] - b[3]) if abs(a[3] - b[3]) > 1e-6 else u
    cx = a[1] + (b[1] - a[1])*k; cy = a[2] + (b[2] - a[2])*k
    return sy, cx, cy, w
def view_at(t, keys):
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys[:-1], keys[1:]):
        if t <= t1: return interp_view(v0, v1, (t - t0)/max(t1 - t0, 1e-6))
    return keys[-1][1]
FULL = (960.0, 540.0, 1920.0)
def full_on(rect, sy):
    x, y, w, h = rect; return (sy, x + w/2, y - sy + h/2, w)

def shot_bounds(kind):
    for s in T.SHOTS:
        if s[2] == 'feed' and s[3]['kind'] == kind: return s[0], s[1]
def neighbour_cams(t0, t1):
    nxt = next(s for s in T.SHOTS if s[0] >= t1 - 1e-6 and s[2] == 'stage')
    prev = next((s for s in reversed(T.SHOTS) if s[1] <= t0 + 1e-6 and s[2] == 'stage'), nxt)
    pc = E.shot_cam(prev[1] - 1e-3, prev[0], prev[1], prev[3]) if prev is not nxt else E.shot_cam(nxt[0], nxt[0], nxt[1], nxt[3])
    return pc, E.shot_cam(nxt[0], nxt[0], nxt[1], nxt[3])

# ------------------------------------------------------------------ definicje przebitek
def words_typed(key, t, start=None):
    toks = _tokens(key); out = [tk for tk, t0 in toks if t >= t0 - 0.02]
    return ' '.join(out)
K = {}
def _def():
    a, b = shot_bounds('open')
    vid = R('main', 'video')
    K['open'] = dict(states=[(0, 'main_play'), (2.29, 'main')],
                     view=[(0.0, (0, 960, 540, 1920)), (2.29, (0, 935, 560, 1680)), (3.27, full_on(vid, 0))],
                     cursor=[(0.3, (1560, 930)), (1.2, (1200, 760)), (2.05, (vid[0] + vid[2]/2 + 6, vid[1] + vid[3]/2 + 8)), (3.3, (vid[0] + vid[2]/2 + 6, vid[1] + vid[3]/2 + 8))],
                     clicks=[2.29], freeze_until=2.29, video_cam=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): neighbour_cams(a, b)[1])
    a, b = shot_bounds('henio_post'); pc, nc = neighbour_cams(a, b)
    K['henio_post'] = dict(states=[(a, 'hp_c0'), (27.9, 'hp_c1'), (28.5, 'hp_c2'), (29.1, 'hp_c3')],
                           view=[(a, full_on(vid, 0)), (a + 0.72, (0, 960, 545, 1840)), (b - 0.75, (0, 975, 560, 1740)), (b, full_on(vid, 0))],
                           reacts=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 3 + 1479*smoothstep((t - a)/2.6)**0.6, ncomments=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): sum(t >= x for x in (27.9, 28.5, 29.1)),
                           chat=(1, 4), video_cam=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): pc if t < (a + b)/2 else nc)
    a, b = shot_bounds('to_grazyna'); pc, nc = neighbour_cams(a, b)
    gi = R('grz', 'grazynaImg')
    K['to_grazyna'] = dict(states=[(a, 'grz')],
                           view=[(a, full_on(vid, 0)), (a + 0.7, (0, 960, 540, 1920)), (80.3, (0, 960, 540, 1920)), (81.9, (560, 960, 540, 1920)),
                                 (82.05, (560, 960, 540, 1920)), (b, full_on(gi, 560))],
                           cursor=[(80.2, (1150, 300)), (81.9, (1150, 420)), (82.05, (gi[0] + gi[2]*0.62, gi[1] - 560 + gi[3]*0.55))],
                           reacts=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 1482, ncomments=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 3, chat=(5, 0), video_cam=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): pc, gimg_cam=nc, gimg_t=b)
    a, b = shot_bounds('analytics'); pc, nc = neighbour_cams(a, b)
    K['analytics'] = dict(states=[(a, 'an_empty')],
                          view=[(a, (0, 925, 610, 1380)), (T.lt(T.CH2, 3), (0, 925, 625, 1300)), (T.lt(T.CH2, 3) + 1.0, (170, 920, 640, 1180)), (b, (170, 915, 650, 1120))],
                          reacts=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 1482 + 8*smoothstep((t - a)/6), views=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 98120 + (1254302 - 98120)*smoothstep((t - a - 0.1)/3.0)**0.7,
                          ncomments=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 0, comment=[(T.CH2, 2, a, T.lt(T.CH2, 3)), (T.CH2, 3, T.lt(T.CH2, 3), b)],
                          video_cam=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): pc if t < (a + b)/2 else nc)
    a, b = shot_bounds('simple_post'); pc, nc = neighbour_cams(a, b)
    vid2 = R('simple1', 'video')
    K['simple_post'] = dict(states=[(a, 'simple0'), (165.4, 'simple1')],
                            view=[(a, (0, 915, 410, 1250)), (166.3, (0, 925, 420, 1180)), (166.9, (353, 960, 540, 1920)), (b, full_on(vid2, 353))],
                            simple_reacts=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): sum(t >= x for x in (164.5, 165.0, 165.6)), simple_comments=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 1 if t >= 165.4 else 0,
                            reacts=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 1497, ncomments=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 0, video_cam=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): nc, video_rect='simple1')
    a, b = shot_bounds('outro'); pc, nc = neighbour_cams(a, b)
    mcu = Cam(0.0, -320.0, 1150.0, 1700.0)
    K['outro'] = dict(states=[(a, 'outro')],
                      view=[(a, full_on(vid, 0)), (a + 0.75, (0, 960, 545, 1880)), (191.3, (0, 960, 545, 1880)), (192.9, (1500, 960, 540, 1920)),
                            (193.45, (0, 960, 540, 1920)), (b, full_on(vid, 0))],
                      reacts=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 1497, ncomments=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 0, comment=[(T.OUT, 0, a, b)],
                      cursor=[(191.0, (1250, 820)), (192.9, (1250, 700)), (193.45, (1180, 620))],
                      video_cam=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): pc if t < a + 0.6 else (mcu if t < 193.0 else nc))
    a, b = shot_bounds('stats'); pc, nc = neighbour_cams(a, b)
    K['stats'] = dict(states=[(a, 'stats0'), (205.4, 'stats1')],
                      view=[(a, full_on(vid, 0)), (a + 0.7, (0, 935, 600, 1460)), (b - 0.65, (0, 935, 610, 1380)), (b, full_on(vid, 0))],
                      reacts=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 4, views=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 1254302 + 40*(t - a), ncomments=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): 1 if t >= 205.4 else 0,
                      video_cam=lambda t, a=a, b=b, pc=locals().get('pc'), nc=locals().get('nc'), mcu=locals().get('mcu'): pc if t < (a + b)/2 else nc)
_def()

# ------------------------------------------------------------------ rysowanie
_GIMG = {}
def _stage_img(t, cam, key=None):
    if key is not None and key in _GIMG: return _GIMG[key]
    surf = skia.Surface(E.W, E.H); cv = surf.getCanvas()
    sc = T.stage_scene(t, cam); CP.render_stage(cv, sc, t)
    im = surf.makeImageSnapshot()
    if key is not None: _GIMG[key] = im
    return im
def _text(cv, s, x, y, size, color=(0, 0, 0, 0.9), weight='ui', align='left'):
    f = font(weight, size); w = f.measureText(s)
    if align == 'right': x -= w
    cv.drawString(s, x, y, f, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(*color)))
    return w
def _cursor(cv, x, y, press=0.0):
    p = skia.Path(); pts = [(0, 0), (0, 22), (5.5, 17), (9.5, 26), (13, 24.5), (9, 16), (16, 16)]
    p.moveTo(*pts[0]); [p.lineTo(*q) for q in pts[1:]]; p.close()
    cv.save(); cv.translate(x, y); s = 1.25 - 0.15*press; cv.scale(s, s)
    sh = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.3)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 2))
    cv.save(); cv.translate(1.5, 2); cv.drawPath(p, sh); cv.restore()
    cv.drawPath(p, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 1)))
    cv.drawPath(p, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6, Color4f=skia.Color4f(1, 1, 1, 1)))
    cv.restore()

def film_amount(t, sc):
    """0 = widok strony, 1 = pełny kadr filmu (do płynnego przejścia obróbki obrazu)."""
    D = K[sc['kind']]; sy, cx, cy, w = view_at(t, D['view'])
    return float(np.clip((1920.0/w - 1.5)/(3.46 - 1.5), 0, 1))
def render_feed(cv, t, sc):
    D = K[sc['kind']]
    state = [s for (t0, s) in D['states'] if t >= t0 - 1e-6][-1]
    dpr = META[state]['dpr']
    sy, cx, cy, w = view_at(t, D['view'])
    z = E.W/w
    cv.clear(skia.Color4f(0.956, 0.949, 0.933, 1))
    cv.save()
    cv.translate(E.W/2, E.H/2); cv.scale(z, z); cv.translate(-cx, -cy)
    cv.save(); cv.clipRect(skia.Rect(0, 0, E.W, E.H))
    # strona (przewinięta)
    cv.save(); cv.translate(0, -sy); cv.scale(1/dpr, 1/dpr)
    cv.drawImage(img(state + '_page.png'), 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
    cv.restore()
    # film w poście (scena na żywo)
    vr = R(D.get('video_rect', state), 'video') if D.get('video_rect') else R(state, 'video')
    if vr and vr[2] > 0:
        tv = min(t, D['freeze_until']) if 'freeze_until' in D else t
        im = _stage_img(tv, D['video_cam'](t))
        cv.drawImageRect(im, skia.Rect(vr[0], vr[1] - sy, vr[0] + vr[2], vr[1] - sy + vr[3]), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
        if sc['kind'] == 'open' and t < 2.29:
            cxp, cyp = vr[0] + vr[2]/2, vr[1] - sy + vr[3]/2
            cv.drawCircle(cxp, cyp, 32, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.6)))
            cv.drawCircle(cxp, cyp, 32, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2, Color4f=skia.Color4f(1, 1, 1, 1)))
            tri = skia.Path(); tri.moveTo(cxp - 9, cyp - 14); tri.lineTo(cxp + 15, cyp); tri.lineTo(cxp - 9, cyp + 14); tri.close()
            cv.drawPath(tri, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 1)))
    # zdjęcie we wpisie Grażyny ożywa (kadr, w który wjeżdżamy = pierwsza klatka następnego ujęcia)
    if 'gimg_cam' in D:
        gi = R(state, 'grazynaImg')
        im = _stage_img(D['gimg_t'], D['gimg_cam'], key=('g', D['gimg_t']))
        cv.drawImageRect(im, skia.Rect(gi[0], gi[1] - sy, gi[0] + gi[2], gi[1] - sy + gi[3]), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
    # liczniki (rosną klatka po klatce)
    grey = (0, 0, 0, 0.6)
    rc = R(state, 'bind_reacts')
    if rc and rc[2] > 0 and 'reacts' in D:
        _text(cv, fmt(D['reacts'](t)), rc[0], rc[1] - sy + 13, 12, grey)
    cc = R(state, 'bind_comments')
    if cc and cc[2] > 0 and 'ncomments' in D:
        n = D['ncomments'](t); s = f"{fmt(n)} {plural(n, 'komentarz', 'komentarze', 'komentarzy')} • 12 udostępnień"
        _text(cv, s, cc[0] + cc[2], cc[1] - sy + 13, 12, grey, align='right')
    vw = R(state, 'bind_views')
    if vw and vw[2] > 0 and 'views' in D:
        n = D['views'](t); _text(cv, f"{fmt(n)} {plural(n, 'wyświetlenie', 'wyświetlenia', 'wyświetleń')}", vw[0], vw[1] - sy + 13, 12, (0, 0, 0, 0.6), 'ui_b')
    sr = R(state, 'bind_simpleReacts')
    if sr and sr[2] > 0 and 'simple_reacts' in D:
        _text(cv, fmt(D['simple_reacts'](t)), sr[0], sr[1] - sy + 13, 12, grey)
        scc = R(state, 'bind_simpleComments'); n = D['simple_comments'](t)
        _text(cv, f"{n} {plural(n, 'komentarz', 'komentarze', 'komentarzy')}", scc[0] + scc[2], scc[1] - sy + 13, 12, grey, align='right')
    # pisanie w polu komentarza (wers piosenki słowo po słowie)
    blink = (t*2.2) % 1.0 < 0.6
    for (s_, l_, a_, b_) in D.get('comment', []):
        if a_ <= t < b_:
            ci = R(state, 'commentInput'); txt = words_typed((s_, l_), t)
            x0, y0 = ci[0] + 13, ci[1] - sy + ci[3]/2 + 5
            if not txt: _text(cv, 'Dodaj komentarz…', x0, y0, 14, (0, 0, 0, 0.6))
            wdt = _text(cv, txt, x0, y0, 14, (0, 0, 0, 0.9))
            if blink: cv.drawRect(skia.Rect(x0 + wdt + 1, y0 - 13, x0 + wdt + 2.5, y0 + 4), skia.Paint(Color4f=skia.Color4f(0, 0, 0, 0.85)))
    cv.restore()   # koniec przycięcia do okna przeglądarki
    # pasek nawigacji i dok wiadomości (przypięte do okna)
    cv.save(); cv.scale(1/dpr, 1/dpr); cv.drawImage(img('nav.png'), 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)); cv.restore()
    ox, oy = META[state]['dock_origin']
    cv.save(); cv.translate(ox, oy); cv.scale(1/dpr, 1/dpr); cv.drawImage(img(state + '_dock.png'), 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)); cv.restore()
    if 'chat' in D:
        ch = R(state, 'chatInput'); txt = words_typed(D['chat'], t)
        if ch and ch[2] > 0:
            x0, y0 = ch[0] + 12, ch[1] + 10 + 14
            if not txt: _text(cv, 'Napisz wiadomość…', x0, y0, 14, (0, 0, 0, 0.6))
            else:
                wdt = _text(cv, txt, x0, y0, 14, (0, 0, 0, 0.9))
                if blink: cv.drawRect(skia.Rect(x0 + wdt + 1, y0 - 13, x0 + wdt + 2.5, y0 + 4), skia.Paint(Color4f=skia.Color4f(0, 0, 0, 0.85)))
    # kursor
    if 'cursor' in D:
        ks = D['cursor']
        if ks[0][0] <= t:
            xs = [k[0] for k in ks]
            px = float(np.interp(t, xs, [k[1][0] for k in ks])); py = float(np.interp(t, xs, [k[1][1] for k in ks]))
            # wygładzenie ruchu kursora (splajn przez klucze)
            from engine import Track
            px, py = Track([(k[0], k[1]) for k in ks])(t)
            press = 0.0
            for c in D.get('clicks', []):
                if 0 <= t - c < 0.25: press = math.sin(math.pi*(t - c)/0.25)
                if 0 <= t - c < 0.6:
                    a = 1 - (t - c)/0.6
                    cv.drawCircle(px, py, 8 + 40*(1 - a), skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color4f=skia.Color4f(0.04, 0.4, 0.76, 0.6*a)))
            fade = 1.0 - film_amount(t, sc)
            if fade > 0.02:
                cv.saveLayerAlpha(None, int(255*fade)); _cursor(cv, px, py, press); cv.restore()
    cv.restore()
