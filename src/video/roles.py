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
    def hold(self, t0, t1, side, fn):
        self.holds.append((t0, t1, side, fn)); return self
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
                    elif not positional and gap > 6.0:
                        out.append((tk - 0.8, vp))           # trzymaj pozę, płynne przejście w ostatnich 0.8 s
                    elif not positional and gap > 1.0:
                        out.append((tk - min(0.45, gap*0.4), vp))   # poza kluczowa trzymana, szybsze przejście do następnej
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
        for (a, b, side, fn) in self.holds:
            if a <= t <= b: props[side].append(lambda cv, fn=fn, t=t: fn(cv, t))
        pose = dict(mouth=mo, smile=self.g('smile', t), turn=turn, tilt=tilt, nod=nod, lean=lean, bob=bob, gaze=(gx, gy), blink=blink,
                    lid=self.g('lid', t), brow=self.g('brow', t), hands={'L': tuple(hL), 'R': tuple(hR)}, props=props)
        # kostium w danej chwili
        for (tc, kw) in self.costume_keys:
            if t >= tc: pose.setdefault('costume', {}).update(kw)
        return Actor(self.ch, x, y + yoff, depth, scale, pose, self.ch.name)
