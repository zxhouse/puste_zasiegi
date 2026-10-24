"""Post-produkcja 'ludzka, nie komputerowa': halacja wokół świateł, lekka miękkość, ziarno, winieta.
Wszystko deterministyczne od numeru klatki (bezstanowe)."""
import skia, numpy as np, math
import textures as TX
import engine as E

def _vignette():
    g = skia.GradientShader.MakeRadial(skia.Point(E.W/2, E.H/2), E.W*0.72, [skia.Color4f(1, 1, 1, 1).toColor(), skia.Color4f(1, 1, 1, 1).toColor(), skia.Color4f(0.62, 0.6, 0.6, 1).toColor()], [0, 0.55, 1])
    p = skia.Paint(); p.setShader(g); p.setBlendMode(skia.BlendMode.kMultiply); return p
_VIG = None
_BRIGHT = skia.ColorFilters.Matrix([1.6, 0, 0, 0, -0.75,
                                    0, 1.45, 0, 0, -0.72,
                                    0, 0, 1.3, 0, -0.7,
                                    0, 0, 0, 1, 0])
def _grade():
    """Gradacja: krzywa S (kontrast w półtonach, głębsze cienie, miękko zaokrąglone światła) + lekko więcej nasycenia."""
    x = np.arange(256)/255.0
    s_ = x*x*(3 - 2*x)
    y = np.clip((0.62*x + 0.38*s_ - 0.015)/0.985, 0, 1)
    tab = [int(v) for v in (y*255 + 0.5).astype(np.uint8)]
    curve = skia.TableColorFilter.MakeARGB(None, tab, tab, tab)
    k = 1.08; lr, lg, lb = 0.2126, 0.7152, 0.0722
    sat = skia.ColorFilters.Matrix([lr*(1-k)+k, lg*(1-k), lb*(1-k), 0, 0,  lr*(1-k), lg*(1-k)+k, lb*(1-k), 0, 0,
                                    lr*(1-k), lg*(1-k), lb*(1-k)+k, 0, 0,  0, 0, 0, 1, 0])
    return skia.ColorFilters.Compose(curve, sat)
_GRADE = None
def apply(surface, frame_idx, halation=0.6, grain=1.0, soft=0.4, vignette=1.0, grade=1.0):
    global _VIG
    cv = surface.getCanvas()
    img = surface.makeImageSnapshot()
    # 1) halacja: jasne partie -> rozmycie -> ciepły, dodany blask
    small = skia.Surface(E.W//4, E.H//4)
    sc = small.getCanvas()
    p = skia.Paint(); p.setColorFilter(_BRIGHT)
    sc.drawImageRect(img, skia.Rect(0, 0, E.W//4, E.H//4), skia.SamplingOptions(skia.FilterMode.kLinear), p)
    glow = small.makeImageSnapshot()
    cv.save(); cv.resetMatrix()
    # 2) miękkość: lekkie rozmycie całości (obiektyw/kamera studyjna)
    global _GRADE
    if _GRADE is None: _GRADE = _grade()
    if soft > 0 or grade > 0:
        bp = skia.Paint()
        if soft > 0: bp.setImageFilter(skia.ImageFilters.Blur(soft, soft))
        if grade > 0: bp.setColorFilter(_GRADE)
        cv.drawImage(img, 0, 0, skia.SamplingOptions(), bp)
    if halation > 0:
        gp = skia.Paint(); gp.setBlendMode(skia.BlendMode.kPlus)
        gp.setImageFilter(skia.ImageFilters.Blur(9, 9))
        gp.setColorFilter(skia.ColorFilters.Matrix([0.55*halation, 0, 0, 0, 0, 0, 0.32*halation, 0, 0, 0, 0, 0, 0.2*halation, 0, 0, 0, 0, 0, 1, 0]))
        cv.save(); cv.scale(4, 4); cv.drawImage(glow, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), gp); cv.restore()
    # 3) winieta
    if _VIG is None: _VIG = _vignette()
    if vignette > 0:
        vp = skia.Paint(_VIG); vp.setAlphaf(vignette); cv.drawRect(skia.Rect(0, 0, E.W, E.H), vp)
    # 4) ziarno (klatka ziarna i przesunięcie zależne od numeru klatki)
    if grain > 0:
        G = TX.grain_frames()
        gk = frame_idx//2                 # ziarno zmienia się co 2 klatki (spokojniejsze, lepiej znosi kompresję)
        gi = G[gk % len(G)]
        rng = np.random.default_rng(gk*7919 + 13)
        dx, dy = rng.integers(0, 64, 2)
        sh = gi.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear),
                           skia.Matrix.Translate(-float(dx), -float(dy)).preScale(2.0, 2.0))
        gp = skia.Paint(); gp.setShader(sh); gp.setBlendMode(skia.BlendMode.kOverlay); gp.setAlphaf(0.12*grain)
        cv.drawRect(skia.Rect(0, 0, E.W, E.H), gp)
    cv.restore()
