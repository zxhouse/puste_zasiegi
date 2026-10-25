"""Silnik bezstanowy: dane analizy, splajny, akcenty z perkusji, ruch ust, kamera z paralaksą warstw."""
import json, os, math, numpy as np
ROOT = os.environ.get('PZ_ROOT') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H, FPS = 1920, 1080, 30
SONG_DUR = 212.04
TAIL = 24.0          # napisy końcowe (v6: 2x szybsze, na zasuniętej kurtynie - credits.duration() = ok. 23 s)
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
# Dane: analysis/alignment.json (v3: Omnilingual CTC + MFA). Każda sylaba ma własne otwarcie 0..1 (samogłoska x głośność x
# długość x akcent) - stąd półotwarcia; między sylabami szczęka przymyka się do 'dołka' (pełne zamknięcie przed m/b/p
# i w przerwach, częściowe między innymi spółgłoskami), więc każda sylaba to osobny, widoczny ruch szczęki.
ROUND = {'o': 0.8, 'ó': 1.0, 'u': 1.0, 'ą': 0.6, 'y': 0.2, 'a': 0.0, 'e': 0.0, 'ę': 0.1, 'i': 0.0}
LABIAL = ('m', 'b', 'p')
GAP = 0.037          # minimalne zamknięcie ust między sylabami (> 1 klatka przy 30 kl./s)
def _syl_list(singer):
    out = []
    for L in AL['lines'] + AL.get('repeats', []):
        for w in L['words']:
            if singer not in w['singers']: continue
            if singer == 'choir' and 'syl_choir' in w: syl, op = w['syl_choir'], w['open_choir']
            else: syl, op = w['syl'], w['open']
            for s, o in zip(syl, op):
                out.append(dict(on=s['t_on'], pk=s['t_peak'], off=s['t_off'], open=o, round=ROUND.get(s['vowel'], 0.2),
                                labial=s['text'].lower().startswith(LABIAL), spoken=L['spoken']))
    out.sort(key=lambda d: d['on'])
    return out
def _choir_extra():
    """Chór: wokalizy bez słów ('uuu', 'aaa' - zaokrąglone usta, trzymane) i okrzyki 'hej'."""
    out = []
    ev = sorted(e['t_on'] for e in AL['choir']['events'])
    for seg in AL['choir']['wordless']:
        on_s = [e for e in ev if seg['t0'] - 0.05 <= e <= seg['t1']] or [seg['t0']]
        if on_s[0] > seg['t0'] + 0.15: on_s = [seg['t0']] + on_s
        for i, on in enumerate(on_s):
            off = on_s[i+1] - 0.02 if i + 1 < len(on_s) else seg['t1']
            if off - on < 0.12: continue
            out.append(dict(on=on, pk=on + 0.08, off=off, open=0.55, round=1.0, labial=False, spoken=False))
    for h in AL['choir']['hej']:
        out.append(dict(on=h['t_on'] - 0.02, pk=h['t_on'] + 0.05, off=h['t_on'] + 0.38, open=1.0, round=0.0, labial=False, spoken=False))
    fh = AL['choir']['finale'][-1]                      # końcowe "HEJ" - wszyscy
    out.append(dict(on=fh['t_on'] - 0.02, pk=fh['t_on'] + 0.05, off=fh['t_on'] + 0.9, open=1.0, round=0.0, labial=False, spoken=False))
    return out
def _curve(sylls, n_frames):
    """Krzywa otwarcia i zaokrąglenia ust na siatce klatek. Gwarancje: w każdej sylabie >=1 klatka z otwarciem >= 0,8 jej
    poziomu; między sąsiednimi sylabami >=1 klatka z dołkiem <= 40% mniejszego z dwóch otwarć (pełne zero przy m/b/p i przerwach)."""
    m = np.zeros(n_frames + 2); r = np.zeros(n_frames + 2)
    sylls = sorted(sylls, key=lambda d: d['on'])
    for k, s in enumerate(sylls):
        nxt = sylls[k+1] if k + 1 < len(sylls) else None
        on = s['on'] - 0.012; pk = max(s['pk'], on + 0.035)
        off = s['off'] if nxt is None else min(s['off'], nxt['on'] - 0.012)
        off = max(off, pk + 0.03)
        f0 = max(int(math.ceil(on*FPS - 1e-6)), 0); f1 = min(int(math.floor(off*FPS + 1e-6)), n_frames + 1)
        for f in range(f0, f1 + 1):
            t = f/FPS
            rise = smoothstep((t - on)/max(pk - on, 0.03))
            hold = 1.0 - 0.15*smoothstep((t - pk)/max(min(off - pk, 0.4), 0.05))   # długa nuta: lekkie przymknięcie, potem trzyma
            fall = smoothstep((off - t)/min(0.08, max((off - pk)*0.5, 0.03)))
            v = s['open']*rise*hold*fall
            if v > m[f]: m[f] = v; r[f] = s['round']
        # gwarancja wyraźnego otwarcia: klatka najbliższa szczytu
        fp = min(max(int(round(pk*FPS)), f0), max(f1, f0))
        if fp < len(m): m[fp] = max(m[fp], 0.85*s['open']); r[fp] = s['round']
    # dołki między sylabami
    for k in range(1, len(sylls)):
        a, b = sylls[k-1], sylls[k]
        gap = b['on'] - a['off']
        depth = 0.0 if (b['labial'] or gap > 0.10) else 0.32*min(a['open'], b['open'])
        fa = int(round(max(a['pk'], a['on'] + 0.035)*FPS)); fb = int(round(max(b['pk'], b['on'] + 0.035)*FPS))
        fd = int(round((b['on'] - 0.012)*FPS))
        fd = min(max(fd, fa + 1), fb - 1) if fb - fa >= 2 else None
        if fd is None:                                   # sylaby w sąsiednich klatkach: przesuń szczyt następnej o klatkę
            fb = fa + 2; fd = fa + 1
            if fb < len(m): m[fb] = max(m[fb], 0.85*b['open']); r[fb] = b['round']
        if 0 <= fd < len(m): m[fd] = min(m[fd], depth)
    return m, r
def _extend_held(S, DB, drop=12.0, gate=34.0):
    """Koniec otwarcia = koniec głosu w stemie (v7, w obie strony): ostatnia chwila przed następną sylabą, w której poziom stemu
    (RMS co 10 ms) jest nie niżej niż `drop` dB pod szczytem tej sylaby i nad bramką (max - `gate` dB). Szukane od końca, więc
    chwilowe przygaśnięcia długiej nuty (vibrato, oddech w środku) nie ucinają otwarcia; pogłos poniżej progu go nie przedłuża.
    Najdalej 40 ms przed następną sylabą, najkrócej 60 ms po szczycie sylaby."""
    S.sort(key=lambda d: d['on']); top = float(DB.max())
    for k in range(len(S) - 1, 0, -1):          # ta sama sylaba z dwóch źródeł (np. końcowe 'HEJ'): jedna, dłuższa
        if S[k]['on'] - S[k-1]['on'] < 0.05:
            S[k-1]['off'] = max(S[k-1]['off'], S[k]['off']); S[k-1]['open'] = max(S[k-1]['open'], S[k]['open']); del S[k]
    for k, s in enumerate(S):
        nxt = S[k+1]['on'] if k + 1 < len(S) else s['off'] + 4.0
        i0 = int(s['on']*100); i1 = int(max(min(s['off'], nxt), s['on'] + 0.05)*100)
        if i0 >= len(DB): continue
        pk = float(DB[i0:i1 + 1].max())
        lim = min(int((nxt - 0.04)*100), len(DB) - 1)
        seg = DB[i0:lim]
        above = np.nonzero(seg > max(pk - drop, top - gate))[0]
        end = (i0 + above[-1] + 1)/100 if len(above) else s['off']
        end = min(max(end, max(s['pk'], s['on']) + 0.06), nxt - 0.04)
        if abs(end - s['off']) > 0.005: s['off_al'] = s.get('off_al', s['off']); s['off'] = end
    return S
LEAD_SYLS = _syl_list('lead')
for f in AL['choir']['finale']:                          # okrzyki Henia w finale ("hej" 201,5 s i "HEJ" 209,8 s)
    LEAD_SYLS.append(dict(on=f['t_on'] - 0.02, pk=f['t_on'] + 0.05, off=f['t_off'], open=1.0, round=0.0, labial=False, spoken=False))
_extend_held(LEAD_SYLS, LEAD_DB)
LEAD_ON = np.array(sorted(s['on'] for s in LEAD_SYLS))
LEAD_MOUTH, LEAD_ROUND = _curve(LEAD_SYLS, N_FRAMES)
def _frame_lookup(arr, t):
    x = t*FPS; i = int(math.floor(x + 1e-6)); f = x - i
    if f < 1e-4: return float(arr[min(max(i, 0), len(arr) - 1)])
    i = min(max(i, 0), len(arr) - 2); return float(arr[i]*(1 - f) + arr[i+1]*f)
def lead_mouth(t):
    return _frame_lookup(LEAD_MOUTH, t)
def lead_round(t):
    return _frame_lookup(LEAD_ROUND, t)
CHOIR_SYLS = _extend_held(_syl_list('choir') + _choir_extra(), BACK_DB)
CHOIR_MOUTH, CHOIR_ROUND = _curve(CHOIR_SYLS, N_FRAMES)
def choir_mouth(t, member=0):
    """Chór: wspólny czas (śpiewają razem), amplituda lekko różna między lalkami."""
    k = 0.88 + 0.12*math.sin(member*1.7)
    return _frame_lookup(CHOIR_MOUTH, t)*k
def choir_round(t):
    return _frame_lookup(CHOIR_ROUND, t)
def singing(t, singer='lead', pad=0.15):
    """Czy w chwili t dany głos śpiewa (do gestów i ekspresji)."""
    S = LEAD_SYLS if singer == 'lead' else CHOIR_SYLS
    return any(s['on'] - pad <= t <= s['off'] + pad for s in S[max(0, _idx(S, t) - 3):_idx(S, t) + 2])
def _idx(S, t):
    lo, hi = 0, len(S)
    while lo < hi:
        mid = (lo + hi)//2
        if S[mid]['on'] < t: lo = mid + 1
        else: hi = mid
    return lo

# ---------------------------------------------------------------- kamera z perspektywą warstw
class Cam:
    __slots__ = ('x', 'y', 'd', 'f', 'roll', 'yaw')
    def __init__(self, x=0.0, y=-260.0, d=2000.0, f=1700.0, roll=0.0, yaw=0.0):
        self.x, self.y, self.d, self.f, self.roll, self.yaw = x, y, d, f, roll, yaw
    def lerp(self, o, a):
        return Cam(self.x + (o.x - self.x)*a, self.y + (o.y - self.y)*a, self.d*(o.d/self.d)**a, self.f + (o.f - self.f)*a,
                   self.roll + (o.roll - self.roll)*a, self.yaw + (o.yaw - self.yaw)*a)
    def scale(self, depth=0.0): return self.f/(self.d + depth)
    def _homo(self, depth):
        """v8: kamera na orbicie wokół punktu (x, y) na płaszczyźnie sceny, obrócona o yaw (stopnie) - każda warstwa jest
        płaszczyzną, więc jej obraz to homografia (dokładna perspektywa, przy yaw=0 zwykłe skalowanie)."""
        a = math.radians(self.yaw); c, s = math.cos(a), math.sin(a); f = self.f; n = self.d + depth
        return [f*c/n, 0.0, f*(-c*self.x - s*depth)/n,
                0.0, f/n, -f*self.y/n,
                s/n, 0.0, (-s*self.x + self.d + c*depth)/n]
    def apply(self, cv, depth=0.0):
        """Ustawia macierz kanwy dla warstwy na głębokości depth (+ za płaszczyzną sceny, - przed nią)."""
        cv.translate(W/2, H/2)
        if self.roll: cv.rotate(self.roll)
        if abs(self.yaw) < 1e-6:
            s = self.scale(depth); cv.scale(s, s); cv.translate(-self.x, -self.y)
        else:
            import skia
            cv.concat(skia.Matrix.MakeAll(*self._homo(depth)))
    def to_screen(self, x, y, depth=0.0):
        m = self._homo(depth); w = m[6]*x + m[8]
        u, v = (m[0]*x + m[2])/w, (m[4]*y + m[5])/w
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
