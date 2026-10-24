"""Role: lalka + obecność na scenie + klucze póz (splajny) + ruch proceduralny zależny tylko od t."""
import math, numpy as np, hashlib
from collections import defaultdict
import engine as E
from engine import Track, smoothstep
from compose import Actor

def _hash01(*a):
    h = hashlib.md5(repr(a).encode()).digest(); return int.from_bytes(h[:4], 'little')/2**32

# energia ruchu w częściach utworu (bujanie, kiwnięcia)
ENERGY = Track([(0, 0.25), (13.5, 0.35), (14.2, 0.5), (30.0, 0.55), (33.2, 0.7), (46.6, 0.75), (59.4, 1.0), (79.0, 0.9),
                (79.4, 0.6), (102.5, 0.7), (115.8, 0.8), (127.6, 1.0), (147.6, 0.9), (148.8, 0.15), (163.9, 0.2), (166.6, 0.6),
                (167.8, 1.0), (186.9, 0.9), (188.6, 0.4), (194.6, 0.9), (202.5, 0.6), (212.0, 0.3)])

SNAPPY = ('hL', 'hR', 'lean', 'turn', 'tilt')

def _sing_state(syls, ons, t):
    """Ekspresja śpiewu z sylab (czysta funkcja t): akcent sylaby (impuls na początku, waga = otwarcie), długa nuta (0..1)."""
    i = int(np.searchsorted(ons, t + 0.03)) - 1
    acc = 0.0; longn = 0.0
    for j in range(max(i - 3, 0), i + 1):
        sy = syls[j]; dt = t - sy['on']
        if dt < -0.03: continue
        acc += sy['open']*(smoothstep((dt + 0.03)/0.05) if dt < 0.02 else math.exp(-(dt - 0.02)/0.13))
        dur = sy['off'] - sy['on']
        if dur > 0.45 and sy['on'] + 0.18 < t < sy['off']:
            longn = max(longn, smoothstep((t - sy['on'] - 0.18)/0.35)*smoothstep((sy['off'] - t)/0.15))
    return min(acc, 1.4), longn
_LEAD_ON = np.array([s['on'] for s in E.LEAD_SYLS]); _CH_SYLS = sorted(E.CHOIR_SYLS, key=lambda d: d['on']); _CH_ON = np.array([s['on'] for s in _CH_SYLS])

class Role:
    def __init__(self, ch, mouth='none', member=0, base=None):
        self.ch, self.mouth, self.member = ch, mouth, member
        self.spans = []        # (t_in, t_out, entry, exit, din, dout)
        self.k = defaultdict(list)
        self.holds = []        # (t0, t1, side, fn(cv, t))
        self.mouth_windows = []  # (t0, t1) gdy usta mają podążać za źródłem (domyślnie zawsze)
        self.costume_keys = []   # (t, dict) zmiany kostiumu
        self.base = dict(x=0.0, y=0.0, depth=0.0, scale=1.0, hL=(-150.0, -30.0), hR=(150.0, -30.0), gaze=(0.0, 0.1), brow=0.0,
                         lid=ch.lid, smile=0.0, turn=0.0, lean=0.0, tilt=0.0, jitter=1.0)
        if base: self.base.update(base)
        self.tracks = None
    def on(self, t_in, t_out, entry='rise', exit='sink', din=0.55, dout=0.45):
        self.spans.append((t_in, t_out, entry, exit, din, dout)); return self
    def key(self, t, **kw):
        for k, v in kw.items(): self.k[k].append((t, v))
        return self
    def hold(self, t0, t1, side, fn, grip=False):
        """Rekwizyt w dłoni. grip=True: dłoń zaciśnięta na drążku/przedmiocie (rekwizyt rysowany pod pięścią)."""
        self.holds.append((t0, t1, side, fn, grip)); return self
    def costume(self, t, **kw):
        self.costume_keys.append((t, kw)); return self
    def build(self):
        self.tracks = {}
        for k, v in self.k.items():
            v = sorted(v, key=lambda kv: kv[0])
            out = []
            positional = k in ('x', 'y', 'depth', 'scale')
            for i, (tk, val) in enumerate(v):
                if i > 0:
                    tp, vp = v[i-1]
                    gap = tk - tp
                    if positional and gap > 3.0:
                        out.append((tk - 0.02, vp))          # trzymaj pozycję, przeskok dopiero przy następnym kluczu (cięcie)
                    elif not positional and k in SNAPPY and gap > 0.22:
                        # ruch lalkarski: poza trzymana do ostatniej chwili, szybki ruch z lekkim przestrzałem i powrotem
                        dur = min(0.30, max(gap*0.5, 0.12))
                        a = np.asarray(vp, float); b = np.asarray(val, float)
                        out.append((tk - dur, vp))
                        os_ = b + 0.08*(b - a)
                        out.append((tk - 0.02, tuple(os_) if np.ndim(os_) else float(os_)))
                        out.append((tk + min(0.16, gap*0.3), val))
                        continue
                    elif not positional and gap > 6.0:
                        out.append((tk - 0.8, vp))           # trzymaj pozę, płynne przejście w ostatnich 0.8 s
                    elif not positional and gap > 1.0:
                        out.append((tk - min(0.35, gap*0.4), vp))   # poza kluczowa trzymana, szybsze przejście do następnej
                out.append((tk, val))
            self.tracks[k] = Track(out)
        self.costume_keys.sort(key=lambda c: c[0])
        return self
    def g(self, name, t):
        tr = self.tracks.get(name)
        if tr is None: return self.base[name]
        v = tr(t); return v
    def span_at(self, t):
        for s in self.spans:
            if s[0] - (s[4] if s[2] == 'rise' else 0) <= t <= s[1] + s[5]: return s
        return None

    def actor(self, t):
        sp = self.span_at(t)
        if sp is None: return None
        t_in, t_out, entry, exit_, din, dout = sp
        x = self.g('x', t); y = self.g('y', t); depth = self.g('depth', t); scale = self.g('scale', t)
        yoff = 0.0
        if entry == 'rise' and t < t_in: yoff = 520*(1 - smoothstep((t - (t_in - din))/din))
        if exit_ == 'sink' and t > t_out: yoff = 520*smoothstep((t - t_out)/dout)
        if entry in ('left', 'right') and t < t_in + din:
            sgn = -1 if entry == 'left' else 1; x += sgn*1500*(1 - smoothstep((t - t_in)/din))
        if exit_ in ('left', 'right') and t > t_out:
            sgn = -1 if exit_ == 'left' else 1; x += sgn*1500*smoothstep((t - t_out)/dout)
        if yoff > 515: return None
        en = ENERGY(t)*self.g('jitter', t)
        ph = _hash01(self.ch.name, 'ph')
        # --- ruch proceduralny: bujanie w siatce bitów, sprężyste kiwnięcia na stopie/werblu
        k_hit = E.kick(t, decay=0.14); s_hit = E.snare(t, decay=0.12)
        sway = E.beat_sway(t, 2.0, ph)
        lean = self.g('lean', t) + 2.6*en*sway
        bob = -(5 + 7*en)*k_hit*en - 3.0*en*abs(E.beat_sway(t, 1.0, ph*0.3))
        nod = 9*en*(0.7*k_hit + 0.6*s_hit)
        # obrót w stronę ruchu (chód)
        dx = (self.g('x', t + 0.05) - self.g('x', t - 0.05))/0.1
        if entry in ('left', 'right') and t < t_in + din: dx += (1500/din)*(1 if entry == 'left' else -1)*0.5
        if exit_ in ('left', 'right') and t > t_out: dx += (1500/dout)*(-1 if exit_ == 'left' else 1)*0.5
        turn = self.g('turn', t)
        walk = min(abs(dx)/250, 1.0)
        if walk > 0.05:
            turn = turn*(1 - walk) + math.copysign(0.75, dx)*walk
            bob -= 14*walk*abs(math.sin(t*2*math.pi*2.2))
            lean += 5*walk*math.copysign(1, dx)
        # usta
        mo = 0.0
        if self.mouth == 'lead': mo = E.lead_mouth(t)
        elif self.mouth == 'choir': mo = E.choir_mouth(t, self.member)
        mo = max(mo, self.g('mouth_extra', t) if 'mouth_extra' in self.k else 0.0)
        if 'mouth_mute' in self.k: mo *= 1 - self.g('mouth_mute', t)
        tilt = self.g('tilt', t) + 4*mo*math.sin(t*3.1 + ph*6) + 1.5*en*E.beat_sway(t, 4.0, ph + 0.25)
        # ekspresja śpiewu: kiwnięcie głową na akcentowanych sylabach, długie nuty - głowa w górę i przymknięte oczy
        lid_add = 0.0; brow_add = 0.0
        if self.mouth in ('lead', 'choir'):
            acc, longn = _sing_state(E.LEAD_SYLS, _LEAD_ON, t) if self.mouth == 'lead' else _sing_state(_CH_SYLS, _CH_ON, t)
            k_ = 1.0 if self.mouth == 'lead' else 0.7
            nod += k_*(11*acc - 16*longn)
            tilt += k_*(5*longn*math.sin(ph*6 + 1.0) + 2.5*acc*math.sin(t*1.7 + ph*4))
            lean += k_*(-2.5*longn + 1.5*acc)
            lid_add = 0.32*longn; brow_add = 0.35*longn + 0.25*min(acc, 1.0)
        # taniec tylko tam, gdzie niesie go piosenka (refreny, finał): krok w bok co 2 bity, sprężynowanie na stopie
        if en > 0.82:
            dk = smoothstep((en - 0.82)/0.18)
            step = math.sin(math.pi*E.beat_pos(t) + ph*2.0)
            x += dk*16*step*self.g('scale', t)
            lean += dk*4.5*step
            bob -= dk*10*k_hit
        # mruganie (deterministyczne)
        blink = 0.0
        period = 3.2 + 1.8*_hash01(self.ch.name, 'bl')
        kb = math.floor(t/period); tb = kb*period + _hash01(self.ch.name, kb)*period*0.6
        if 0 <= t - tb < 0.16: blink = math.sin(math.pi*(t - tb)/0.16)
        gx, gy = self.g('gaze', t)
        gx += 0.12*math.sin(t*0.7 + ph*9); gy += 0.06*math.sin(t*0.9 + ph*5)
        hL = np.array(self.g('hL', t)); hR = np.array(self.g('hR', t))
        # dłonie: lekki ruch wtórny (bujanie prętów)
        hL = hL + np.array([4*math.sin(t*2.1 + ph*7), 6*en*k_hit + 3*math.sin(t*1.7 + ph)])
        hR = hR + np.array([4*math.sin(t*2.3 + ph*3), 6*en*k_hit + 3*math.sin(t*1.9 + ph*2)])
        props = {'L': [], 'R': []}
        grips = {'L': False, 'R': False}
        for (a, b, side, fn, grip) in self.holds:
            if a <= t <= b:
                props[side].append((lambda cv, fn=fn, t=t: fn(cv, t), grip)); grips[side] = grips[side] or grip
        rnd = E.lead_round(t) if self.mouth == 'lead' else (E.choir_round(t) if self.mouth == 'choir' else 0.0)
        pose = dict(mouth=mo, round=rnd, smile=self.g('smile', t), turn=turn, tilt=tilt, nod=nod, lean=lean, bob=bob, gaze=(gx, gy), blink=blink,
                    lid=min(self.g('lid', t) + lid_add, 0.85), brow=self.g('brow', t) + brow_add, hands={'L': tuple(hL), 'R': tuple(hR)}, props=props, grip=grips)
        # kostium w danej chwili
        for (tc, kw) in self.costume_keys:
            if t >= tc: pose.setdefault('costume', {}).update(kw)
        return Actor(self.ch, x, y + yoff, depth, scale, pose, self.ch.name)
