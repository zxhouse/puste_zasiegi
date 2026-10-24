"""Post-produkcja 'ludzka, nie komputerowa': halacja wokół świateł, lekka miękkość, ziarno, winieta.
Wszystko deterministyczne od numeru klatki (bezstanowe).
v4: halacja i gradacja liczone razem (blask dodany PRZED krzywą tonalną, która ma miękkie 'ramię' w światłach -
nic nie przepala się do płaskiej bieli), drobne i słabe ziarno (odporne na kompresję serwisów)."""
import skia, numpy as np, math
import textures as TX
import engine as E

def _vignette():
    g = skia.GradientShader.MakeRadial(skia.Point(E.W/2, E.H/2), E.W*0.72, [skia.Color4f(1, 1, 1, 1).toColor(), skia.Color4f(1, 1, 1, 1).toColor(), skia.Color4f(0.62, 0.6, 0.6, 1).toColor()], [0, 0.55, 1])
    p = skia.Paint(); p.setShader(g); p.setBlendMode(skia.BlendMode.kMultiply); return p
_VIG = None
# tylko naprawdę jasne partie (żarówki, odblaski) świecą: próg ~0.82
_BRIGHT = skia.ColorFilters.Matrix([2.4, 0, 0, 0, -1.95,
                                    0, 2.3, 0, 0, -1.9,
                                    0, 0, 2.2, 0, -1.85,
                                    0, 0, 0, 1, 0])
def tone(x):
    """Krzywa tonalna: łagodne S w półtonach + miękkie ramię w światłach (biel wejścia -> ~0.93, a nie płaskie 1.0)."""
    s_ = x*x*(3 - 2*x)
    y = np.clip((0.66*x + 0.34*s_ - 0.012)/0.988, 0, None)
    k = 0.74; r = 0.95 - k
    return np.where(y < k, y, k + r*np.tanh((y - k)/r))
def _grade():
    """Gradacja: krzywa tonalna z ramieniem + lekko więcej nasycenia."""
    x = np.arange(256)/255.0
    y = tone(x)
    tab = [int(v) for v in np.clip(y*255 + 0.5, 0, 255).astype(np.uint8)]
    curve = skia.TableColorFilter.MakeARGB(None, tab, tab, tab)
    k = 1.08; lr, lg, lb = 0.2126, 0.7152, 0.0722
    sat = skia.ColorFilters.Matrix([lr*(1-k)+k, lg*(1-k), lb*(1-k), 0, 0,  lr*(1-k), lg*(1-k)+k, lb*(1-k), 0, 0,
                                    lr*(1-k), lg*(1-k), lb*(1-k)+k, 0, 0,  0, 0, 0, 1, 0])
    return skia.ColorFilters.Compose(curve, sat)
_GRADE = None
def apply(surface, frame_idx, halation=0.3, grain=1.0, soft=0.4, vignette=1.0, grade=1.0):
    global _VIG, _GRADE
    cv = surface.getCanvas()
    img = surface.makeImageSnapshot()
    if _GRADE is None: _GRADE = _grade()
    cv.save(); cv.resetMatrix()
    # 1) miękkość (obiektyw kamery studyjnej) + halacja: jasne partie -> rozmycie -> ciepły blask (screen, nie dodawanie)
    if soft > 0:
        bp = skia.Paint(); bp.setImageFilter(skia.ImageFilters.Blur(soft, soft)); cv.drawImage(img, 0, 0, skia.SamplingOptions(), bp)
    if halation > 0:
        small = skia.Surface(E.W//4, E.H//4)
        p = skia.Paint(); p.setColorFilter(_BRIGHT)
        small.getCanvas().drawImageRect(img, skia.Rect(0, 0, E.W//4, E.H//4), skia.SamplingOptions(skia.FilterMode.kLinear), p)
        glow = small.makeImageSnapshot()
        gp = skia.Paint(); gp.setBlendMode(skia.BlendMode.kScreen)
        gp.setImageFilter(skia.ImageFilters.Blur(8, 8))
        gp.setColorFilter(skia.ColorFilters.Matrix([0.5*halation, 0, 0, 0, 0, 0, 0.36*halation, 0, 0, 0, 0, 0, 0.26*halation, 0, 0, 0, 0, 0, 1, 0]))
        cv.save(); cv.scale(4, 4); cv.drawImage(glow, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), gp); cv.restore()
    # 2) gradacja na całości (już z blaskiem): krzywa z ramieniem w światłach
    if grade > 0:
        img2 = surface.makeImageSnapshot()
        gp = skia.Paint(); gp.setColorFilter(_GRADE); gp.setAlphaf(grade)
        cv.drawImage(img2, 0, 0, skia.SamplingOptions(), gp)
    # 3) winieta
    if _VIG is None: _VIG = _vignette()
    if vignette > 0:
        vp = skia.Paint(_VIG); vp.setAlphaf(vignette); cv.drawRect(skia.Rect(0, 0, E.W, E.H), vp)
    # 4) ziarno: drobne (1 px tekstury = 1 px obrazu), słabe, zmienia się co 2 klatki - kompresja serwisów go nie 'rozmaże w bloki'
    if grain > 0:
        G = TX.grain_frames()
        gk = frame_idx//2
        gi = G[gk % len(G)]
        rng = np.random.default_rng(gk*7919 + 13)
        dx, dy = rng.integers(0, 64, 2)
        sh = gi.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear),
                           skia.Matrix.Translate(-float(dx), -float(dy)))
        gp = skia.Paint(); gp.setShader(sh); gp.setBlendMode(skia.BlendMode.kOverlay); gp.setAlphaf(0.055*grain)
        cv.drawRect(skia.Rect(0, 0, E.W, E.H), gp)
    cv.restore()
