"""Pomocnicze funkcje graficzne: czcionki (OFL z folderu fonts/), tektura, malowany tekst, światła."""
import skia, math, numpy as np, os, functools
from puppet import Material, fill, poly_path, col, shade, mix
import textures as TX
from engine import ROOT
FONTS = {
    # świat lalek: kroje wystawowe (OFL, Google Fonts) - pełne polskie znaki sprawdzone fontTools
    'sign': 'fonts/bajaderka/Bajaderka-Regular.otf', 'marquee': 'fonts/rammettoone/RammettoOne-Regular.ttf',
    'script': 'fonts/shrikhand/Shrikhand-Regular.ttf', 'block': 'fonts/sigmarone/SigmarOne-Regular.ttf',
    'block2': 'fonts/titanone/TitanOne-Regular.ttf', 'hand': 'fonts/kalam/Kalam-Bold.ttf', 'brush': 'fonts/caveatbrush/CaveatBrush-Regular.ttf',
    'bubbly': 'fonts/cherrybombone/CherryBombOne-Regular.ttf',
    # napisy końcowe i świat serwisu (bez zmian)
    'credits': 'fonts/montserrat/Montserrat-ExtraBold.otf', 'credits2': 'fonts/montserrat/Montserrat-Medium.otf',
    'ui': 'fonts/inter/Inter-Regular.otf', 'ui_b': 'fonts/inter/Inter-SemiBold.otf'}
@functools.lru_cache(None)
def typeface(name): return skia.Typeface.MakeFromFile(os.path.join(ROOT, FONTS[name]))
@functools.lru_cache(None)
def font(name, size):
    f = skia.Font(typeface(name), size); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True); return f
def text_width(text, fname, size): return font(fname, size).measureText(text)
def draw_text(cv, text, x, y, fname, size, color, align='center', shadow=None, stroke=None, alpha=1.0, maxw=None):
    """maxw: najszerszy dopuszczalny napis (z obrysem) - większy jest proporcjonalnie zmniejszany, linia bazowa zostaje."""
    if maxw:
        w0 = font(fname, size).measureText(text) + (stroke[1] if stroke else 0)
        if w0 > maxw: size = size*maxw/w0
    f = font(fname, size); w = f.measureText(text)
    x0 = x - w/2 if align == 'center' else (x - w if align == 'right' else x)
    if shadow:
        sp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, shadow[2]*alpha)); sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow[3] if len(shadow) > 3 else 3))
        cv.drawString(text, x0 + shadow[0], y + shadow[1], f, sp)
    if stroke:
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=stroke[1], Color4f=col(stroke[0], alpha) if isinstance(stroke[0], str) else stroke[0], StrokeJoin=skia.Paint.kRound_Join)
        cv.drawString(text, x0, y, f, p)
    c = col(color, alpha) if isinstance(color, str) else skia.Color4f(color.fR, color.fG, color.fB, color.fA*alpha)
    cv.drawString(text, x0, y, f, skia.Paint(AntiAlias=True, Color4f=c))
    return w

def card(cv, rect, color, r=10, tex='card', seed=3, edge=0.6, light=1.12, dark=0.82, wobble=0.0):
    """Prostokąt z tektury/sklejki: lekko nierówne krawędzie, cieniowanie, faktura, ciemniejszy rant."""
    x0, y0, x1, y1 = rect
    if wobble:
        rng = np.random.default_rng(seed)
        pts = []
        for (ax, ay, bx, by) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
            for u in np.linspace(0, 1, 6, endpoint=False):
                pts.append((ax + (bx - ax)*u + rng.normal(0, wobble), ay + (by - ay)*u + rng.normal(0, wobble)))
        p = poly_path(pts, True, True)
    else:
        p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect(x0, y0, x1, y1), r, r))
    fill(cv, p, Material(color, tex, 0.9, light=light, dark=dark, seed=seed))
    if edge:
        c = col(color) if isinstance(color, str) else color
        e = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4, Color4f=shade(c, edge))
        cv.drawPath(p, e)
    return p

def drop_shadow(cv, path, dx=10, dy=14, blur=14, alpha=0.35):
    p = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, alpha)); p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    cv.save(); cv.translate(dx, dy); cv.drawPath(path, p); cv.restore()

def light_pool(cv, x, y, rx, ry, color=(1.0, 0.92, 0.75), alpha=0.5):
    """Plama światła reflektora (tryb 'screen': rozjaśnia, ale nigdy nie przepala do bieli)."""
    cv.save(); cv.translate(x, y); cv.scale(1, ry/rx)
    g = skia.GradientShader.MakeRadial(skia.Point(0, 0), rx, [skia.Color4f(*color, alpha).toColor(), skia.Color4f(*color, alpha*0.5).toColor(), skia.Color4f(*color, 0).toColor()], [0, 0.55, 1])
    p = skia.Paint(AntiAlias=True); p.setShader(g); p.setBlendMode(skia.BlendMode.kScreen)
    cv.drawCircle(0, 0, rx, p); cv.restore()

def beam(cv, x0, y0, x1, y1, w0, w1, color=(1.0, 0.95, 0.8), alpha=0.18):
    """Snop światła w zadymieniu (trapez z gradientem)."""
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); nx, ny = -dy/L, dx/L
    pts = [(x0 + nx*w0, y0 + ny*w0), (x1 + nx*w1, y1 + ny*w1), (x1 - nx*w1, y1 - ny*w1), (x0 - nx*w0, y0 - ny*w0)]
    g = skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)], [skia.Color4f(*color, alpha).toColor(), skia.Color4f(*color, 0).toColor()])
    p = skia.Paint(AntiAlias=True); p.setShader(g); p.setBlendMode(skia.BlendMode.kScreen)
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
    cv.drawPath(poly_path(pts, True, False), p)

def bulb(cv, x, y, r, on, color=(1.0, 0.85, 0.5)):
    k = min(max(on, 0.0), 1.0)      # v8.1: jasność płynnie (wcześniej przełączana skokowo przy 0,5 - żarówki 'mrugały')
    lerp = lambda a, b: skia.Color4f(*[a[i] + (b[i] - a[i])*k for i in range(3)], 1).toColor()
    g = skia.GradientShader.MakeRadial(skia.Point(x - r*0.3, y - r*0.3), r*1.3,
                                       [lerp((0.55, 0.5, 0.42), (1, 1, 0.95)), lerp((0.3, 0.27, 0.22), color)], [0, 1])
    p = skia.Paint(AntiAlias=True); p.setShader(g); cv.drawCircle(x, y, r, p)
    if on > 0.05:
        light_pool(cv, x, y, r*4.5, r*4.5, color, 0.35*on)

def stripes_path(x0, y0, x1, y1, n, vertical=True):
    paths = []
    for i in range(n):
        if vertical:
            a = x0 + (x1 - x0)*i/n; b = x0 + (x1 - x0)*(i + 0.5)/n; paths.append(skia.Rect(a, y0, b, y1))
        else:
            a = y0 + (y1 - y0)*i/n; b = y0 + (y1 - y0)*(i + 0.5)/n; paths.append(skia.Rect(x0, a, x1, b))
    return paths
