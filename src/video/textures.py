"""Proceduralne tekstury (deterministyczne, bez plików z internetu): filc, futro, tektura, ziarno."""
import numpy as np, skia, functools, scipy.ndimage as nd

def _to_image(a, alpha=None):
    a = np.clip(a, 0, 255).astype(np.uint8)
    if a.ndim == 2:
        rgba = np.dstack([a, a, a, np.full_like(a, 255) if alpha is None else np.clip(alpha, 0, 255).astype(np.uint8)])
    else:
        rgba = np.dstack([a, np.full(a.shape[:2], 255, np.uint8) if alpha is None else alpha.astype(np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.ColorType.kRGBA_8888_ColorType)

def tile_noise(n, scale, seed):
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((n, n))
    # filtr w dziedzinie częstotliwości -> bezszwowa (okresowa) tekstura
    fx = np.fft.fftfreq(n)[:, None]; fy = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fx**2 + fy**2)
    spec = np.fft.fft2(a)*np.exp(-(f*n/scale)**2)
    b = np.real(np.fft.ifft2(spec)); return b/(b.std() + 1e-9)

@functools.lru_cache(None)
def felt(seed=1, n=512):
    """Filc: drobne splątane włókna + niskoczęstotliwościowa niejednorodność. Wartości ~1.0 (do mnożenia)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((n, n))
    # włókna: krótkie odcinki o losowych kierunkach (zawijane okresowo)
    for _ in range(9000):
        x, y = rng.uniform(0, n, 2); ang = rng.uniform(0, np.pi); L = rng.uniform(4, 16)
        ts = np.linspace(0, L, int(L*1.5))
        xs = (x + np.cos(ang)*ts + rng.normal(0, 0.6, len(ts)).cumsum()*0.3).astype(int) % n
        ys = (y + np.sin(ang)*ts + rng.normal(0, 0.6, len(ts)).cumsum()*0.3).astype(int) % n
        img[ys, xs] += rng.uniform(0.4, 1.0)*rng.choice([-1, 1])
    img = nd.gaussian_filter(img, 0.7, mode='wrap')
    img = img/(img.std() + 1e-9)*0.045 + tile_noise(n, 9, seed+1)*0.03 + tile_noise(n, 60, seed+2)*0.02
    return _to_image(243*(1 + img))       # ~0.95 średnio: lekkie przyciemnienie + faktura włókien

@functools.lru_cache(None)
def cardboard(seed=3, n=512):
    rng = np.random.default_rng(seed)
    g = tile_noise(n, 70, seed)*0.04 + tile_noise(n, 12, seed+1)*0.025
    # delikatne pionowe prążki (karton falisty prześwitujący)
    x = np.arange(n)[None, :]
    g += 0.02*np.sin(2*np.pi*x/n*48)
    return _to_image(240*(1 + g))

@functools.lru_cache(None)
def velvet(seed=5, n=512):
    g = tile_noise(n, 30, seed)*0.05 + tile_noise(n, 5, seed+1)*0.03
    return _to_image(238*(1 + g))

@functools.lru_cache(None)
def grain_frames(k=12, w=960, h=540, seed=11):
    """Zestaw klatek ziarna (wybierany deterministycznie z numeru klatki)."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(k):
        g = rng.standard_normal((h, w))
        g = nd.gaussian_filter(g, 0.6)
        g = g/g.std()
        out.append(_to_image(128 + 128*np.clip(g*0.5, -1, 1)))
    return out

def shader_of(img, scale=1.0, dx=0, dy=0):
    m = skia.Matrix.Scale(scale, scale); m.postTranslate(dx, dy)
    return img.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear), m)
