"""Napisy jako część scenografii. Jeden wers = jedno stałe miejsce w świecie sceny; słowa pojawiają się w momencie
zaśpiewania (czasy słów z analysis/alignment.json). Każdy znak zwraca też swój prostokąt (do kontroli kolizji i do
kadrowania - kamera obejmuje napis razem z postacią).
v4: rozmiar tablicy liczony z rzeczywistego obrysu glifów (z polskimi znakami nad i pod linią) + zapas na 'wyskok'
słowa, więc tekst nigdy nie wychodzi poza pole; tablica bez obwódki; dymek to jeden kontur (prostokąt i ogonek
złączone operacją na ścieżkach), ogonek wskazuje usta mówiącego."""
import skia, math, re
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
    L = LINES[key]
    # tekst do wyświetlenia: oryginalny wers bez nawiasów chóru i cudzysłowów prostych
    t = re.sub(r'\(.*?\)', '', L['text']).replace('"', '').strip()
    if not t:                             # wers śpiewany tylko przez chór, np. "(Wywalili na bruk!)"
        t = re.sub(r'[()"]', '', L['text']).strip()
    return t

def _tokens(key):
    """Słowa w pisowni z tekstu (z interpunkcją) + czasy pojawienia się. Sam znak (np. myślnik) dokleja się do
    poprzedniego słowa (nie zaczyna nowej linijki i nie wisi samotnie)."""
    txt = line_text(key).split()
    ws = words_of(key)
    out = []; i = 0
    for tok in txt:
        core = re.sub(r"[^A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]", '', tok)
        if not core:
            if tok.strip('—–-') == '': continue          # pauzy (myślniki) z tekstu nie są wyświetlane
            if out: out[-1] = (out[-1][0] + ' ' + tok, out[-1][1])
            else: out.append((tok, ws[0][1]))
            continue
        if i < len(ws): out.append((tok, ws[i][1])); i += 1
        else: out.append((tok, ws[-1][1]))
    return out

def _row_w(row, fname, size): return text_width(' '.join(t for t, _ in row), fname, size)
def _best_split(tokens, n, fname, size):
    """Podział na n linijek minimalizujący najdłuższą (wyważone linijki)."""
    if n == 1: return [tokens], _row_w(tokens, fname, size)
    best = None
    for k in range(1, len(tokens) - n + 2):
        rest, m = _best_split(tokens[k:], n - 1, fname, size)
        mm = max(_row_w(tokens[:k], fname, size), m)
        if best is None or mm < best[1] - 1e-6: best = ([tokens[:k]] + rest, mm)
    return best
def _fit_lines(tokens, fname, size, maxw, max_rows=3):
    """Najmniej linijek, przy których wers mieści się w maxw; gdy nawet 3 nie wystarczą - mniejszy krój (nigdy poza pole)."""
    s = size
    for _ in range(12):
        for n in range(1, min(max_rows, len(tokens)) + 1):
            rows, m = _best_split(tokens, n, fname, s)
            if m <= maxw: return rows, s
        s *= 0.93
    return _best_split(tokens, min(max_rows, len(tokens)), fname, s)[0], s

POP = 0.06       # słowo 'wyskakuje' o 6% w chwili zaśpiewania (mniej - nie 'zjada' spacji)
def _block(rows, fname, size, line_h):
    """Pozycje linii bazowych (względem środka bloku) i dokładny obrys bloku tekstu (z ogonkami i kreskami nad literami)."""
    f = font(fname, size)
    tops, bots, widths, wmax = [], [], [], 0.0
    for r, row in enumerate(rows):
        b = skia.Rect(); s = ' '.join(t for t, _ in row)
        widths.append(f.measureText(s, skia.TextEncoding.kUTF8, b))
        tops.append(r*line_h + b.top()); bots.append(r*line_h + b.bottom())
        for tk, _ in row: wmax = max(wmax, f.measureText(tk))
    c = (min(tops) + max(bots))/2
    base = [r*line_h - c for r in range(len(rows))]
    return base, max(widths), max(bots) - min(tops), wmax

def _draw_tokens(cv, rows, t, fname, size, color, cx, cy, line_h, glow=None, stroke=None, pop=True, base=None):
    """Słowa pojawiają się w chwili zaśpiewania. base: linie bazowe względem cy (z _block); bez - stary układ."""
    f = font(fname, size)
    for r, row in enumerate(rows):
        full = ' '.join(tk for tk, _ in row)
        W = text_width(full, fname, size)
        x = cx - W/2
        y = cy + (base[r] if base is not None else (r - (len(rows) - 1)/2)*line_h + size*0.35)
        sp = text_width(' ', fname, size)
        for tk, t0 in row:
            w = text_width(tk, fname, size)
            a = smoothstep((t - t0 + 0.02)/0.07)
            if a > 0.01:
                s = 1.0 + (POP*(1 - smoothstep((t - t0)/0.16)) if pop else 0)
                ym = y - size*0.33
                cv.save(); cv.translate(x, ym); cv.scale(s, s); cv.translate(-x, -ym)      # od lewej krawędzi słowa: nie zjada spacji przed nim
                if glow: light_pool(cv, x + w/2, y - size*0.3, w*0.7, size*0.9, glow, 0.22*a)
                draw_text(cv, tk, x, y, fname, size, color, 'left', stroke=stroke, alpha=a)
                cv.restore()
            x += w + sp

def _card(cv, path, color, seed, tex_alpha=0.42, edge=0.72, tex_scale=1.4):
    """Gładka tektura: miękki gradient światła + delikatna faktura (słabsza niż w dekoracjach - napis ma być czytelny
    i dobrze znosić kompresję) + ciemniejszy rant."""
    m = Material(color, 'card', tex_scale, light=1.06, dark=0.9, seed=seed)
    b = path.getBounds(); cv.drawPath(path, m.paint((b.left(), b.top(), b.right(), b.bottom())))
    tp = skia.Paint(m.tex_paint()); tp.setAlphaf(tex_alpha); cv.drawPath(path, tp)
    c = col(color) if isinstance(color, str) else color
    cv.drawPath(path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.5, Color4f=shade(c, edge)))

BOXED = ('board', 'bubble', 'marker')
FONT_OF = {'board': 'block2', 'riser': 'bubbly', 'playboard': 'bubbly', 'marquee': 'marquee', 'curtain': 'script', 'bubble': 'hand',
           'marker': 'brush', 'neon': 'script', 'placard': 'hand'}
class Sign:
    def __init__(self, key, kind, x=0.0, y=-650.0, depth=40.0, size=64, t_in=None, t_out=None, maxw=1500, **kw):
        self.key, self.kind, self.x, self.y, self.depth = key, kind, x, y, depth
        L = LINES[key]
        self.t0 = (t_in if t_in is not None else L['t0'] - 0.35)
        self.t1 = (t_out if t_out is not None else L['t1'] + 0.55)
        self.cut_in = kw.pop('cut_in', None)    # wers zaczyna się na cięciu: tablica po prostu wisi już w nowym ujęciu (nie wjeżdża w poprzednim)
        self.hard_out = kw.pop('hard_out', False)  # napis kończy się na cięciu: znika razem z ujęciem (bez wygaszania przed cięciem)
        self.kw = kw
        self.tokens = _tokens(key)
        self.fname = kw.get('font', FONT_OF[kind])
        self.layout(size, maxw)
    def layout(self, size, maxw=None, tokens=None):
        """Łamanie wersu i wymiary pola: z rzeczywistego obrysu tekstu + marginesy + zapas na powiększenie słowa."""
        if tokens is not None: self.tokens = tokens
        if maxw is not None: self.maxw = maxw
        if self.kind == 'marquee':          # tablica portalu ma stałe pole: 1-2 linijki w 980 x 150 jednostek
            self.maxw = min(self.maxw, 980.0)
            self.rows, self.size = _fit_lines(self.tokens, self.fname, size, self.maxw, max_rows=2)
            while len(self.rows)*self.size*1.08 > 150: self.size *= 0.95; self.rows, self.size = _fit_lines(self.tokens, self.fname, self.size, self.maxw, max_rows=2)
        else:
            self.rows, self.size = _fit_lines(self.tokens, self.fname, size, self.maxw)
        s = self.size
        self.line_h = s*(1.16 if self.kind in BOXED else (1.08 if self.kind == 'marquee' else 1.12))
        self.base, bw, bh, wmax = _block(self.rows, self.fname, s, self.line_h)
        if self.kind in BOXED:
            padx = (0.62 if self.kind == 'bubble' else 0.5)*s + POP/2*wmax + 4
            pady = (0.46 if self.kind == 'bubble' else 0.36)*s + POP/2*s + 4
        else:
            padx = 0.12*s + POP/2*wmax; pady = 0.1*s + POP/2*s
        self.w = bw + 2*padx; self.h = bh + 2*pady
        return self
    def active(self, t): return (self.t0 - 0.4 if self.cut_in is None else self.cut_in) <= t < self.t1
    def rect(self):
        if self.kind == 'bubble':     # z ogonkiem
            tx, ty = self._tail()[2]
            return (min(self.x - self.w/2, self.x + tx), self.y - self.h/2, max(self.x + self.w/2, self.x + tx), max(self.y + self.h/2, self.y + ty))
        return (self.x - self.w/2, self.y - self.h/2, self.x + self.w/2, self.y + self.h/2)
    def box_rect(self):
        return (self.x - self.w/2, self.y - self.h/2, self.x + self.w/2, self.y + self.h/2)
    # ---------------------------------------------------------------- dymek: jeden kontur
    def _tail(self):
        """Ogonek dymka: podstawa na dolnej krawędzi (bliżej mówiącego), czubek w stronę ust (względem środka dymka)."""
        tgt = self.kw.get('tail_to')               # punkt w świecie (usta mówiącego)
        w, h = self.w, self.h
        dx, dy = (tgt[0] - self.x, tgt[1] - self.y) if tgt is not None else (-0.3*w, 1.2*h)
        r = min(0.32*h, 46.0)
        bx = max(-w/2 + r + 0.06*w, min(w/2 - r - 0.06*w, dx*0.55))
        base_w = min(0.16*w, 0.5*h, 90.0)
        L = math.hypot(dx - bx, dy - h/2)
        ln = min(max(0.55*h, 50.0), 0.75*L) if L > 1 else 0.6*h
        ux, uy = ((dx - bx)/L, (dy - h/2)/L) if L > 1 else (0.0, 1.0)
        if uy < 0.35: ux, uy = math.copysign(math.sqrt(1 - 0.35**2), ux), 0.35
        tip = (bx + ux*ln, h/2 + uy*ln)
        return (bx - base_w/2, h/2 - 2), (bx + base_w/2, h/2 - 2), tip
    def _bubble_path(self):
        w, h = self.w, self.h
        r = min(0.32*h, 46.0)
        body = skia.Path(); body.addRRect(skia.RRect.MakeRectXY(skia.Rect(-w/2, -h/2, w/2, h/2), r, r))
        (ax, ay), (bx, by), (tx, ty) = self._tail()
        tail = skia.Path(); tail.moveTo(ax, ay - 10)
        # boki ogonka lekko wklęsłe (jak rysowany dymek komiksowy)
        mx1, my1 = (ax + tx)/2 + 0.12*(by - ty), (ay + ty)/2
        tail.quadTo(mx1, my1, tx, ty)
        mx2, my2 = (bx + tx)/2 - 0.04*(by - ty), (by + ty)/2
        tail.quadTo(mx2, my2, bx, by - 10); tail.close()
        return skia.Op(body, tail, skia.PathOp.kUnion_PathOp) or body
    # ---------------------------------------------------------------- rysowanie
    def draw(self, cv, t):
        if not self.active(t): return
        k = self.kind
        fin = smoothstep((t - (self.t0 - 0.35))/0.35) if self.cut_in is None else 1.0
        fout = (1.0 if self.hard_out else smoothstep((self.t1 - t)/0.3)) if t < self.t1 else 0.0
        vis = min(fin, fout)
        if vis <= 0.001: return
        ink = self.kw.get('ink', '#2b1d14')
        if k == 'board':           # tablica z tektury na dwóch sznurkach, zjeżdża z góry
            dy = -900*(1 - fin)**1.6
            w, h = self.w, self.h
            cv.save(); cv.translate(self.x, self.y + dy + 4*math.sin(t*1.4 + self.x)); cv.rotate(0.8*math.sin(t*0.9 + self.x*0.01))
            if fout < 1: cv.saveLayerAlpha(None, int(255*fout))
            sx = min(w*0.36, w/2 - 30)
            p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.5, Color4f=col('#d9d2c3'))
            cv.drawLine(-sx, -h/2 + 14, -sx*1.02, -2600, p); cv.drawLine(sx, -h/2 + 14, sx*1.02, -2600, p)
            r = min(0.16*h, 26.0)
            body = skia.Path(); body.addRRect(skia.RRect.MakeRectXY(skia.Rect(-w/2, -h/2, w/2, h/2), r, r))
            drop_shadow(cv, body, 10, 14, 16, 0.32)
            _card(cv, body, self.kw.get('color', '#f3e5c2'), hash(self.key) % 50 + 400)
            for s_ in (-1, 1):       # oczka na sznurek
                cv.drawCircle(s_*sx, -h/2 + 14, 6.5, skia.Paint(AntiAlias=True, Color4f=col('#b9ad96')))
                cv.drawCircle(s_*sx, -h/2 + 14, 3.2, skia.Paint(AntiAlias=True, Color4f=col('#5b5040')))
            _draw_tokens(cv, self.rows, t, self.fname, self.size, ink, 0, 0, self.line_h, base=self.base)
            if fout < 1: cv.restore()
            cv.restore()
        elif k == 'bubble':        # dymek: jeden kontur (prostokąt + ogonek), lekko wypukły, rośnie od ogonka
            (ax, ay), (bx_, by_), (tx, ty) = self._tail()
            s = 0.55 + 0.45*smoothstep(vis/1.0)
            cv.save(); cv.translate(self.x, self.y)
            cv.translate(tx, ty); cv.scale(s, s); cv.translate(-tx, -ty)
            if vis < 1: cv.saveLayerAlpha(None, int(255*min(1.0, vis*1.6)))
            path = self._bubble_path()
            drop_shadow(cv, path, 8, 12, 14, 0.28)
            g = skia.GradientShader.MakeLinear([skia.Point(0, -self.h/2), skia.Point(0, self.h/2)], [col('#ffffff').toColor(), col('#eef0f4').toColor()])
            p = skia.Paint(AntiAlias=True); p.setShader(g); cv.drawPath(path, p)
            cv.drawPath(path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4.5, StrokeJoin=skia.Paint.kRound_Join, Color4f=col('#2d3142')))
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#1f2330', 0, 0, self.line_h, pop=False, base=self.base)
            if vis < 1: cv.restore()
            cv.restore()
        elif k == 'marker':        # zwykły karton, pisany markerem (bridge: 'napisać prosto')
            w, h = self.w, self.h
            cv.save(); cv.translate(self.x, self.y + -700*(1 - fin)**1.6)
            if fout < 1: cv.saveLayerAlpha(None, int(255*fout))
            cv.drawLine(0, -h/2, 0, -2600, skia.Paint(AntiAlias=True, StrokeWidth=2.5, Color4f=col('#d8d4c8')))
            body = skia.Path(); body.addRect(skia.Rect(-w/2, -h/2, w/2, h/2))
            drop_shadow(cv, body, 8, 12, 14, 0.3)
            _card(cv, body, '#c9a26b', 300, tex_alpha=0.6, edge=0.62)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#1a1a1a', 0, 0, self.line_h, pop=False, base=self.base)
            if fout < 1: cv.restore()
            cv.restore()
        elif k == 'marquee':       # neon/żarówki na tablicy portalu (tablica jest częścią portalu)
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, self.kw.get('ink', '#ffe08a'), 0, 0, self.line_h,
                         glow=(1.0, 0.75, 0.35), stroke=('#ff8a3d', 3), base=self.base)
            cv.restore()
        elif k == 'curtain':       # malowane złotem na kurtynie
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#f6d47a', 0, 0, self.line_h, stroke=('#5c0a12', 5), base=self.base)
            cv.restore()
        elif k == 'playboard':     # malowane litery na froncie krawędzi sceny (pod lalkami - nigdy ich nie zasłania)
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#f7e9c6', 0, 0, self.line_h, stroke=('#1a1430', max(3, self.size*0.09)),
                         glow=(1.0, 0.8, 0.45), base=self.base)
            cv.restore()
        elif k == 'riser':         # podświetlone litery na froncie podestu chóru (front i tak zasłania korpusy chórzystów)
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, '#fff1c9', 0, 0, self.line_h, stroke=('#2a0d40', max(3, self.size*0.09)),
                         glow=(1.0, 0.75, 0.95), base=self.base)
            cv.restore()
        elif k == 'neon':          # neon na ścianie dekoracji
            cv.save(); cv.translate(self.x, self.y)
            _draw_tokens(cv, self.rows, t, self.fname, self.size, self.kw.get('ink', '#ff7ac6'), 0, 0, self.line_h, glow=(1.0, 0.4, 0.75), stroke=('#ffffff', 2), base=self.base)
            cv.restore()
