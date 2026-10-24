"""Silnik bezstanowy: dane analizy, splajny, akcenty z perkusji, ruch ust, kamera z paralaksą warstw."""
import json, os, math, numpy as np
ROOT = os.environ.get('PZ_ROOT') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H, FPS = 1920, 1080, 30
SONG_DUR = 212.04
TAIL = 4.0
N_FRAMES = int(math.ceil(SONG_DUR*FPS)) + int(TAIL*FPS)

def _j(p): return json.load(open(os.path.join(ROOT, p), encoding='utf-8'))
BEATS = _j('analysis/beats.json'); AL = _j('analysis/alignment.json'); STRUCT = _j('analysis/structure.json')
BT = np.array([b['t'] for b in BEATS['beats']]); BIB = np.array([b['beat_in_bar'] for b in BEATS['beats']])
BACC = np.array([b['accent'] for b in BEATS['beats']])
BARS = BT[BIB == 0]
KICK = np.array([k['t'] for k in BEATS['kick']]); KLVL = np.array([k['lvl'] for k in BEATS['kick']])
SNARE = np.array([k['t'] for k in BEATS['snare']]); SLVL = np.array([k['lvl'] for k in BEATS['snare']])
HAT = np.array([k['t'] for k in BEATS['hat']])
def _norm(l):
    if len(l) == 0: return l
    return np.clip((l - np.percentile(l, 10))/(np.percentile(l, 95) - np.percentile(l, 10) + 1e-9), 0.15, 1.0)
KS, SS = _norm(KLVL), _norm(SLVL)
_V = np.load(os.path.join(ROOT, 'build/vocal_feats.npz'))
LEAD_DB = _V['lead_db']; BACK_DB = _V['back_db']

def beat_pos(t):
    """Ułamkowa pozycja w siatce bitów (lokalnej): 0 = pierwszy bit; zgodna z pływającym tempem."""
    return float(np.interp(t, BT, np.arange(len(BT)), left=(t - BT[0])/BEATS['period'], right=len(BT) - 1 + (t - BT[-1])/BEATS['period']))
def bar_pos(t):
    bp = beat_pos(t); return (bp - BEATS['bar_phase'])/4.0
def bar_time(b):
    return float(np.interp(b*4 + BEATS['bar_phase'], np.arange(len(BT)), BT))

# ---------------------------------------------------------------- splajny
def smoothstep(x): x = min(max(x, 0.0), 1.0); return x*x*(3 - 2*x)
def ease(x, k=0.35):          # ruch z lekkim rozpędzeniem/hamowaniem, ale bez zatrzymania w środku
    x = min(max(x, 0.0), 1.0); return (1 - k)*x + k*smoothstep(x)
class Track:
    """Interpolacja Hermite'a (Catmull-Rom dla nierównych odstępów) między kluczami (t, wartość|wektor)."""
    def __init__(self, keys):
        keys = sorted(keys, key=lambda k: k[0])
        self.t = np.array([k[0] for k in keys], float)
        self.v = np.array([np.atleast_1d(np.asarray(k[1], float)) for k in keys])
        n = len(self.t); self.m = np.zeros_like(self.v)
        # klucze bliżej niż 0.05 s = świadomy skok (cięcie): nie liczymy stycznych przez skok (brak przestrzałów)
        jump = np.r_[np.diff(self.t) < 0.05, False]
        for i in range(1, n - 1):
            if jump[i] or jump[i-1]: continue
            self.m[i] = (self.v[i+1] - self.v[i-1])/(self.t[i+1] - self.t[i-1])
        self.scalar = np.ndim(keys[0][1]) == 0
    def __call__(self, t):
        T, V, M = self.t, self.v, self.m
        if t <= T[0]: r = V[0]
        elif t >= T[-1]: r = V[-1]
        else:
            i = int(np.searchsorted(T, t)) - 1; h = T[i+1] - T[i]; s = (t - T[i])/h
            h00 = 2*s**3 - 3*s**2 + 1; h10 = s**3 - 2*s**2 + s; h01 = -2*s**3 + 3*s**2; h11 = s**3 - s**2
            r = h00*V[i] + h10*h*M[i] + h01*V[i+1] + h11*h*M[i+1]
        return float(r[0]) if self.scalar else r

# ---------------------------------------------------------------- akcenty z prawdziwych uderzeń
def pulses(t, times, strengths=None, attack=0.035, decay=0.16, lookback=1.2):
    """Suma gładkich impulsów (narastanie smoothstep, zanik wykładniczy) w chwilach uderzeń."""
    i1 = np.searchsorted(times, t + attack); i0 = np.searchsorted(times, t - lookback)
    s = 0.0
    for k in range(i0, i1):
        dt = t - times[k]; a = 1.0 if strengths is None else strengths[k]
        if dt < 0: s += a*smoothstep((dt + attack)/attack)*1.0
        else: s += a*math.exp(-dt/decay)
    return s
def kick(t, **kw): return pulses(t, KICK, KS, **kw)
def snare(t, **kw): return pulses(t, SNARE, SS, **kw)
def beat_sway(t, period_beats=2.0, phase=0.0):
    return math.sin(2*math.pi*(beat_pos(t)/period_beats + phase))
def vocal_level(t, which='lead'):
    a = LEAD_DB if which == 'lead' else BACK_DB
    i = int(t*100)
    if i < 0 or i >= len(a): return 0.0
    return float(np.clip((a[i] + 25)/35, 0, 1))

# ---------------------------------------------------------------- usta: jedna sylaba = jedno otwarcie
OPEN = {'a': 1.0, 'o': 0.85, 'ó': 0.6, 'e': 0.8, 'ę': 0.8, 'ą': 0.85, 'u': 0.6, 'y': 0.65, 'i': 0.55}
def _vowel_open(text):
    t = text.lower()
    for ch in t:
        if ch in OPEN and not (ch == 'i' and any(c in OPEN for c in t[t.index(ch)+1:])): return OPEN[ch]
    return 0.6
def _build_syllables():
    syl = []
    for L in AL['lines']:
        if L['singer'] != 'lead': continue
        for w in L['words']:
            for s in w['syl']:
                syl.append((s['t_on'], s['t_peak'], s['t_off'], _vowel_open(s['text']), L['spoken']))
    for e in AL['choir'].get('reprise', []):  # finał: 'Pus-te za-się-gi' w stemie prowadzącym
        syl.append((e['t_on'], e['t_on'] + 0.08, e['t_off'], _vowel_open(e['text']), False))
    syl.sort()
    return np.array([s[:4] for s in syl])
LEAD_SYL = _build_syllables()
LEAD_ON = LEAD_SYL[:, 0]
GAP = 0.037          # minimalne zamknięcie ust między sylabami (> 1 klatka przy 30 kl./s)
def _env(t, on, off, peak_open, rise_len=0.085):
    if t < on or t > off: return 0.0
    dur = off - on
    rise = smoothstep((t - on)/max(min(rise_len, dur*0.45), 0.02))
    fall_len = min(0.09, max(dur*0.35, 0.03))
    fall = smoothstep((off - t)/fall_len)
    return peak_open*rise*fall
def _quantize(sylls, level_fn, n_frames):
    """Usta liczone na siatce klatek: każda sylaba ma >=1 klatkę wyraźnego otwarcia, między sylabami >=1 klatkę zamknięcia.
    sylls: lista (start, koniec_efektywny, otwarcie). Wynik: tablica wartości na klatkę (funkcja czysta numeru klatki)."""
    m = np.zeros(n_frames + 2)
    owner = -np.ones(n_frames + 2, int)
    for k, (s, e, op) in enumerate(sylls):
        f0 = int(math.ceil(s*FPS - 1e-6)); f1 = int(math.floor(e*FPS + 1e-6))
        if f1 < f0: f1 = f0
        f0 = max(f0, 0); f1 = min(f1, n_frames + 1)
        for f in range(f0, f1 + 1):
            v = _env(f/FPS, s, max(e, s + 0.04), op)*(0.72 + 0.28*level_fn(f/FPS))
            if owner[f] >= 0 and owner[f] != k:          # klatka już zajęta przez poprzednią sylabę -> zamknięcie
                continue
            m[f] = v; owner[f] = k
        seg = np.where(owner[f0:f1 + 1] == k)[0] + f0
        if len(seg) and m[seg].max() < 0.45*op:           # bardzo krótka sylaba: wymuś wyraźne otwarcie w środku
            mid = seg[len(seg)//2]; m[mid] = max(m[mid], 0.62*op)
    # zamknięcie między kolejnymi sylabami: jeśli dwie sylaby stykają się klatkami, ostatnia klatka poprzedniej = 0
    for f in range(1, len(m)):
        if owner[f] >= 0 and owner[f-1] >= 0 and owner[f] != owner[f-1] and m[f-1] > 0.05:
            seg_prev = np.where(owner == owner[f-1])[0]
            if len(seg_prev) >= 2: m[f-1] = 0.0
            else:
                seg_cur = np.where(owner == owner[f])[0]
                if len(seg_cur) >= 2: m[f] = 0.0; m[f+1] = max(m[f+1], 0.62*0.8)
    return m
def _lead_sylls():
    out = []
    for i in range(len(LEAD_SYL)):
        on, pk, off, op = LEAD_SYL[i]
        nxt = LEAD_SYL[i+1, 0] if i + 1 < len(LEAD_SYL) else 1e9
        start = on - 0.012
        off_eff = min(off, nxt - 0.012 - GAP) if off > on + 0.06 else min(on + 0.14, nxt - 0.012 - GAP)
        if off_eff - start < 0.075: off_eff = min(start + 0.075, nxt - 0.012 - GAP)
        out.append((start, off_eff, op))
    return out
LEAD_MOUTH = _quantize(_lead_sylls(), lambda t: vocal_level(t, 'lead'), N_FRAMES)
def _frame_lookup(arr, t):
    x = t*FPS; i = int(math.floor(x + 1e-6)); f = x - i
    if f < 1e-4: return float(arr[min(max(i, 0), len(arr) - 1)])
    i = min(max(i, 0), len(arr) - 2); return float(arr[i]*(1 - f) + arr[i+1]*f)
def lead_mouth(t):
    return _frame_lookup(LEAD_MOUTH, t)

BACK_EV = np.array([[e['t_on'], e['t_peak']] for e in AL['choir']['events']])
def _choir_sylls():
    out = []
    for i in range(len(BACK_EV)):
        on = BACK_EV[i, 0]; nxt = BACK_EV[i+1, 0] if i + 1 < len(BACK_EV) else on + 0.6
        off = min(nxt - 0.012 - GAP, on + 0.9)
        out.append((on - 0.012, max(off, on + 0.06), 0.9))
    return out
CHOIR_MOUTH = _quantize(_choir_sylls(), lambda t: vocal_level(t, 'back'), N_FRAMES)
def choir_mouth(t, member=0):
    """Chór: otwarcie na każde zdarzenie sylabowe stemu chórków (amplituda lekko różna między lalkami, czas wspólny)."""
    lv = vocal_level(t, 'back')
    if lv < 0.05: return 0.0
    k = 0.85 + 0.15*math.sin(member*1.7)
    return _frame_lookup(CHOIR_MOUTH, t)*k*(0.6 + 0.4*lv)

# ---------------------------------------------------------------- kamera z perspektywą warstw
class Cam:
    __slots__ = ('x', 'y', 'd', 'f', 'roll')
    def __init__(self, x=0.0, y=-260.0, d=2000.0, f=1700.0, roll=0.0):
        self.x, self.y, self.d, self.f, self.roll = x, y, d, f, roll
    def lerp(self, o, a):
        return Cam(self.x + (o.x - self.x)*a, self.y + (o.y - self.y)*a, self.d*(o.d/self.d)**a, self.f + (o.f - self.f)*a, self.roll + (o.roll - self.roll)*a)
    def scale(self, depth=0.0): return self.f/(self.d + depth)
    def apply(self, cv, depth=0.0):
        """Ustawia macierz kanwy dla warstwy na głębokości depth (+ za płaszczyzną sceny, - przed nią)."""
        s = self.scale(depth)
        cv.translate(W/2, H/2)
        if self.roll: cv.rotate(self.roll)
        cv.scale(s, s); cv.translate(-self.x, -self.y)
    def to_screen(self, x, y, depth=0.0):
        s = self.scale(depth); u, v = (x - self.x)*s, (y - self.y)*s
        if self.roll:
            a = math.radians(self.roll); u, v = u*math.cos(a) - v*math.sin(a), u*math.sin(a) + v*math.cos(a)
        return W/2 + u, H/2 + v
def shot_cam(t, t0, t1, keys, k=0.3):
    """Kamera w ujęciu: klucze [(tau, Cam)] w czasie znormalizowanym 0..1, interpolacja z lekkim easingiem."""
    tau = (t - t0)/max(t1 - t0, 1e-6)
    tau = ease(tau, k)
    for (a, ca), (b, cb) in zip(keys[:-1], keys[1:]):
        if tau <= b: return ca.lerp(cb, (tau - a)/max(b - a, 1e-6))
    return keys[-1][1]
