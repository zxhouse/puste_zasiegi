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

def _fibres(n, count, seed, lmin, lmax, ang_range=(0, np.pi)):
    """Pole krótkich, lekko krętych włókien (bezszwowe), wektorowo: count odcinków po ~1,5 próbki na jednostkę długości."""
    rng = np.random.default_rng(seed)
    img = np.zeros(n*n)
    L = rng.uniform(lmin, lmax, count); ang = rng.uniform(*ang_range, count)
    x0 = rng.uniform(0, n, count); y0 = rng.uniform(0, n, count); w = rng.uniform(0.4, 1.0, count)*rng.choice([-1, 1], count)
    k = int(lmax*1.5) + 1; u = np.linspace(0, 1, k)[None, :]
    wob = rng.normal(0, 0.35, (count, k)).cumsum(1)
    xs = (x0[:, None] + np.cos(ang)[:, None]*L[:, None]*u - np.sin(ang)[:, None]*wob).astype(int) % n
    ys = (y0[:, None] + np.sin(ang)[:, None]*L[:, None]*u + np.cos(ang)[:, None]*wob).astype(int) % n
    np.add.at(img, (ys*n + xs).ravel(), np.repeat(w, k))
    return img.reshape(n, n)
def _mip(img): return img.withDefaultMipmaps()
@functools.lru_cache(None)
def felt(seed=1, n=1024):
    """Filc (v5: 1024², 4x więcej włókien, dwie warstwy grubości, mipmapy - ostry z bliska, bez migotania z daleka).
    Wartości ~0.95 (do mnożenia)."""
    img = nd.gaussian_filter(_fibres(n, 42000, seed, 5, 18), 0.6, mode='wrap')
    img = img/(img.std() + 1e-9)
    fine = nd.gaussian_filter(_fibres(n, 60000, seed + 7, 2, 6), 0.5, mode='wrap'); fine /= fine.std() + 1e-9
    img = img*0.04 + fine*0.022 + tile_noise(n, 14, seed + 1)*0.025 + tile_noise(n, 90, seed + 2)*0.02
    return _mip(_to_image(243*(1 + img)))

@functools.lru_cache(None)
def cardboard(seed=3, n=1024):
    """Tektura (v5: 1024², drobne włókna papieru + plamki, falisty karton prześwitujący, mipmapy)."""
    g = tile_noise(n, 140, seed)*0.035 + tile_noise(n, 24, seed+1)*0.02 + tile_noise(n, 3, seed+3)*0.012
    fib = nd.gaussian_filter(_fibres(n, 30000, seed + 5, 3, 10), 0.5, mode='wrap'); g += fib/(fib.std() + 1e-9)*0.012
    x = np.arange(n)[None, :]
    g += 0.016*np.sin(2*np.pi*x/n*96)
    return _mip(_to_image(240*(1 + g)))

@functools.lru_cache(None)
def velvet(seed=5, n=1024):
    """Aksamit (v5): gęsty, drobny meszek (pionowe włoski) + delikatne smugi wzdłuż fałd zamiast plam; mipmapy."""
    pile = nd.gaussian_filter(_fibres(n, 90000, seed, 2, 5, (np.pi/2 - 0.35, np.pi/2 + 0.35)), 0.45, mode='wrap'); pile /= pile.std() + 1e-9
    rng = np.random.default_rng(seed + 9)
    streak = nd.gaussian_filter(rng.standard_normal((n, n)), (n/10, 1.5), mode='wrap'); streak /= streak.std() + 1e-9
    g = pile*0.035 + streak*0.03 + tile_noise(n, 3, seed + 1)*0.012 + tile_noise(n, 60, seed + 2)*0.012
    return _mip(_to_image(238*(1 + g)))

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
    return img.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), m)
