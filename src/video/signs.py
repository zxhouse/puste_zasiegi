"""Napisy jako część scenografii. Jeden wers = jedno stałe miejsce w świecie sceny; słowa pojawiają się w momencie
zaśpiewania (czasy słów z analysis/alignment.json). Każdy znak zwraca też swój prostokąt (do kontroli kolizji)."""
import skia, math
import engine as E
from engine import smoothstep
from puppet import col, shade, Material, fill, poly_path
from gfx import card, draw_text, text_width, font, light_pool, drop_shadow, bulb

LINES = {}
for L in E.AL['lines']:
    LINES[(L['sec'], L['line'])] = L
def words_of(key):
    L = LINES[key]
    return [(w['w'], w['t0'], w['t1']) for w in L['words']]
def line_text(key):
    import re
    L = LINES[key]
    # tekst do wyświetlenia: oryginalny wers bez nawiasów chóru i cudzysłowów prostych
    t = re.sub(r'\(.*?\)', '', L['text']).replace('"', '').strip()
    if not t:                             # wers śpiewany tylko przez chór, np. "(Wywalili na bruk!)"
        t = re.sub(r'[()"]', '', L['text']).strip()
    return t

def _tokens(key):
    """Słowa w pisowni z tekstu (z interpunkcją) + czasy pojawienia się."""
    txt = line_text(key).split()
    ws = words_of(key)
    out = []; i = 0
    import re
    for tok in txt:
        core = re.sub(r"[^A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]", '', tok)
        if not core:                      # sam znak (—) -> dokleja się do poprzedniego czasu
            out.append((tok, out[-1][1] if out else ws[0][1])); continue
        if i < len(ws): out.append((tok, ws[i][1])); i += 1
        else: out.append((tok, ws[-1][1]))
    return out

def _fit_lines(tokens, fname, size, maxw):
    """Łamanie wersu na maks. 2 linijki, by zmieścił się na tablicy."""
    full = ' '.join(t for t, _ in tokens)
    if text_width(full, fname, size) <= maxw or len(tokens) < 4: return [tokens]
    best = None
    for k in range(2, len(tokens) - 1):
        a = ' '.join(t for t, _ in tokens[:k]); b = ' '.join(t for t, _ in tokens[k:])
        m = max(text_width(a, fname, size), text_width(b, fname, size))
        if best is None or m < best[0]: best = (m, k)
    return [tokens[:best[1]], tokens[best[1]:]]

def _draw_tokens(cv, rows, t, fname, size, color, cx, cy, line_h, glow=None, stroke=None, pop=True):
    for r, row in enumerate(rows):
        full = ' '.join(tk for tk, _ in row)
        W = text_width(full, fname, size)
        x = cx - W/2; y = cy + (r - (len(rows) - 1)/2)*line_h + size*0.35
        sp = text_width(' ', fname, size)
        for tk, t0 in row:
            w = text_width(tk, fname, size)
            a = smoothstep((t - t0 + 0.02)/0.07)
            if a > 0.01:
                s = 1.0 + (0.22*(1 - smoothstep((t - t0)/0.16)) if pop else 0)
                cv.save(); cv.translate(x + w/2, y - size*0.35); cv.scale(s, s); cv.translate(-(x + w/2), -(y - size*0.35))
                if glow: light_pool(cv, x + w/2, y - size*0.3, w*0.7, size*0.9, glow, 0.22*a)
                draw_text(cv, tk, x, y, fname, size, color, 'left', stroke=stroke, alpha=a)
                cv.restore()
            x += w + sp

class Sign:
    def __init__(self, key, kind, x=0.0, y=-650.0, depth=40.0, size=64, t_in=None, t_out=None, maxw=1500, **kw):
        self.key, self.kind, self.x, self.y, self.depth, self.size, self.maxw = key, kind, x, y, depth, size, maxw
        L = LINES[key]
        self.t0 = (t_in if t_in is not None else L['t0'] - 0.35)
        self.t1 = (t_out if t_out is not None else L['t1'] + 0.55)
        self.cut_in = kw.pop('cut_in', None)    # wers zaczyna się na cięciu: tablica po prostu wisi już w nowym ujęciu (nie wjeżdża w poprzednim)
        self.kw = kw
        self.tokens = _tokens(key)
        fname = {'board': 'block2', 'playboard': 'block2', 'marquee': 'marquee', 'curtain': 'script', 'bubble': 'hand', 'marker': 'hand', 'neon': 'script', 'placard': 'hand'}[kind]
        self.fname = kw.get('font', fname)
        self.rows = _fit_lines(self.tokens, self.fname, size, maxw)
        self.w = max(text_width(' '.join(t for t, _ in r), self.fname, size) for r in self.rows) + size*1.4
        self.h = len(self.rows)*size*1.25 + size*0.9
    def active(self, t): return (self.t0 - 0.4 if self.cut_in is None else self.cut_in) <= t < self.t1
    def rect(self):
        return (self.x - self.w/2, self.y - self.h/2, self.x + self.w/2, self.y + self.h/2)
    def draw(self, cv, t):
        if not self.active(t): return
        k = self.kind
        fin = smoothstep((t - (self.t0 - 0.35))/0.35) if self.cut_in is None else 1.0
        fout = smoothstep((self.t1 - t)/0.3) if t < self.t1 else 0.0
        vis = min(fin, fout)
        if vis <= 0.001: return
        if k == 'board':           # tablica z tektury na sznurkach, wjeżdża z góry
            dy = -900*(1 - vis)
            cv.save(); cv.translate(self.x, self.y + dy + 6*math.sin(t*1.4 + self.x))
            p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color4f=col('#d8d4c8'))
            cv.drawLine(-self.w/2 + 40, -self.h/2, -self.w/2 + 40, -2200, p); cv.drawLine(self.w/2 - 40, -self.h/2, self.w/2 - 40, -2200, p)
            path = card(cv, (-self.w/2, -self.h/2, self.w/2, self.h/2), self.kw.get('color', '#f4e6c3'), 14, 'card', hash(self.key) % 50 + 400, 0.55, wobble=3)
            cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-self.w/2 + 12, -self.h/2 + 12, self.w/2 - 12, self.h/2 - 12), 10, 10),
                         skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4, Color4f=col(self.kw.get('trim', '#b5452b'))))
            _draw_tokens(cv, self.rows, t, self.fname, self.size, self.kw.get('ink', '#2b1d14'), 0, 0, self.size*1.2)
            cv.restore()
        elif k == 'marquee':       # neon/żarówki na tablicy portalu (tablica jest częścią portalu)
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, self.kw.get('ink', '#ffe08a'), 0, 0, self.size*1.1,
                         glow=(1.0, 0.75, 0.35), stroke=('#ff8a3d', 3))
            cv.restore()
        elif k == 'curtain':       # malowane złotem na kurtynie
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#f6d47a', 0, 0, self.size*1.15, stroke=('#5c0a12', 5))
            cv.restore()
        elif k == 'bubble':        # dymek z tektury obok mówiącej lalki
            cv.save(); cv.translate(self.x, self.y); s = 0.6 + 0.4*vis; cv.scale(s, s)
            tail = self.kw.get('tail', (-1, 1))
            pp = skia.Path(); pp.addRRect(skia.RRect.MakeRectXY(skia.Rect(-self.w/2, -self.h/2, self.w/2, self.h/2), 40, 40))
            pp.addPath(poly_path([(tail[0]*self.w*0.1, self.h/2 - 6), (tail[0]*self.w*0.36, self.h/2 + 70), (tail[0]*self.w*0.25, self.h/2 - 6)], True, False))
            drop_shadow(cv, pp, 8, 10, 10, 0.3)
            fill(cv, pp, Material('#ffffff', 'card', 0.8, light=1.05, dark=0.9, seed=212))
            cv.drawPath(pp, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=col('#333333')))
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#222222', 0, 0, self.size*1.2, pop=False)
            cv.restore()
        elif k == 'marker':        # zwykły karton, pisany markerem (bridge: 'napisać prosto')
            cv.save(); cv.translate(self.x, self.y + -700*(1 - vis))
            cv.drawLine(0, -self.h/2, 0, -2200, skia.Paint(AntiAlias=True, StrokeWidth=2.5, Color4f=col('#d8d4c8')))
            card(cv, (-self.w/2, -self.h/2, self.w/2, self.h/2), '#c9a26b', 4, 'card', 300, 0.55, wobble=3)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#1a1a1a', 0, 0, self.size*1.2, pop=False)
            cv.restore()
        elif k == 'playboard':     # malowane litery na froncie krawędzi sceny (pod lalkami - nigdy ich nie zasłania)
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#f7e9c6', 0, 0, self.size*1.12, stroke=('#1a1430', max(3, self.size*0.09)),
                         glow=(1.0, 0.8, 0.45))
            cv.restore()
        elif k == 'neon':          # neon na ścianie dekoracji
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, self.kw.get('ink', '#ff7ac6'), 0, 0, self.size*1.15, glow=(1.0, 0.4, 0.75), stroke=('#ffffff', 2))
            cv.restore()
