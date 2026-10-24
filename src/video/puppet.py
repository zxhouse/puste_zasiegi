"""Parametryczna lalka-pacynka (2D, skia). Wszystkie postaci są oryginalne (projekt własny).
Układ lokalny: (0,0) = pas lalki na wysokości krawędzi sceny (playboard), y w górę ujemne.
Rysowanie jest bezstanowe: draw(canvas, pose) gdzie pose to słownik parametrów policzony dla czasu t."""
import numpy as np, skia, math
import textures as TX

def col(h, a=1.0):
    h = h.lstrip('#'); return skia.Color4f(int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255, a)
def shade(c, k):           # k>1 jaśniej, k<1 ciemniej
    return skia.Color4f(min(c.fR*k, 1), min(c.fG*k, 1), min(c.fB*k, 1), c.fA)
def mix(c1, c2, a):
    return skia.Color4f(c1.fR*(1-a)+c2.fR*a, c1.fG*(1-a)+c2.fG*a, c1.fB*(1-a)+c2.fB*a, c1.fA*(1-a)+c2.fA*a)

def poly_path(pts, closed=True, smooth=True):
    p = skia.Path()
    n = len(pts)
    if n < 2: return p
    if not smooth:
        p.moveTo(*pts[0])
        for q in pts[1:]: p.lineTo(*q)
    else:   # Catmull-Rom -> Bezier (gładkie kształty miękkich lalek)
        P = np.asarray(pts, float)
        if closed: P = np.vstack([P[-1:], P, P[:2]])
        else: P = np.vstack([P[:1], P, P[-1:]])
        p.moveTo(*P[1])
        for i in range(1, len(P) - 2):
            p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
            c1 = p1 + (p2 - p0)/6; c2 = p2 - (p3 - p1)/6
            p.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed: p.close()
    return p

def superellipse(w, h, n=2.4, N=96, squash_bottom=1.0):
    t = np.linspace(0, 2*np.pi, N, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    x = w*np.sign(c)*np.abs(c)**(2/n); y = h*np.sign(s)*np.abs(s)**(2/n)
    y = np.where(y > 0, y*squash_bottom, y)
    return np.c_[x, y]

class Material:
    """Wypełnienie: kolor + cieniowanie (światło z lewej-góry) + tekstura (filc/futro/tektura)."""
    def __init__(self, base, tex='felt', tex_scale=0.6, light=1.18, dark=0.72, seed=1):
        self.base = col(base) if isinstance(base, str) else base
        self.tex = tex; self.tex_scale = tex_scale; self.light = light; self.dark = dark; self.seed = seed
    def paint(self, bbox):
        x0, y0, x1, y1 = bbox
        cx, cy = x0 + (x1-x0)*0.32, y0 + (y1-y0)*0.25
        r = max(x1-x0, y1-y0)*0.95
        g = skia.GradientShader.MakeRadial(skia.Point(cx, cy), r, [shade(self.base, self.light).toColor(), self.base.toColor(), shade(self.base, self.dark).toColor()], [0, 0.45, 1])
        p = skia.Paint(AntiAlias=True); p.setShader(g)
        return p
    def tex_paint(self):
        if not self.tex: return None
        key = (self.tex, self.seed % 3 + 1, self.tex_scale, self.seed % 7)
        if key not in _TEXPAINT:
            img = {'felt': TX.felt, 'card': TX.cardboard, 'velvet': TX.velvet}[self.tex](self.seed % 3 + 1)
            sh = TX.shader_of(img, self.tex_scale, (self.seed*137) % 512, (self.seed*251) % 512)
            tp = skia.Paint(AntiAlias=True); tp.setShader(sh); tp.setBlendMode(skia.BlendMode.kMultiply)
            _TEXPAINT[key] = tp
        return _TEXPAINT[key]
_TEXPAINT = {}

def fill(canvas, path, mat):
    b = path.getBounds()
    canvas.drawPath(path, mat.paint((b.left(), b.top(), b.right(), b.bottom())))
    tp = mat.tex_paint()
    if tp is not None: canvas.drawPath(path, tp)

def soft_edge(canvas, path, color, width=3, alpha=0.35):
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width, Color4f=skia.Color4f(color.fR, color.fG, color.fB, alpha))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 1.2))
    canvas.drawPath(path, p)

def fur_fringe(canvas, pts, color, length=26, density=1.0, seed=0, angle_jitter=0.5, width=3.2, outward=None):
    """Futro: krótkie zakrzywione kosmyki wzdłuż krawędzi (deterministyczne z seed)."""
    rng = np.random.default_rng(seed)
    P = np.asarray(pts, float)
    seg = np.diff(np.vstack([P, P[:1]]), axis=0); L = np.hypot(seg[:, 0], seg[:, 1])
    n = int(L.sum()/3.2*density)
    cum = np.r_[0, np.cumsum(L)]
    pos = rng.uniform(0, cum[-1], n)
    idx = np.searchsorted(cum, pos) - 1; idx = np.clip(idx, 0, len(P)-1)
    f = (pos - cum[idx])/np.maximum(L[idx], 1e-6)
    base = P[idx] + seg[idx]*f[:, None]
    tang = seg[idx]/np.maximum(L[idx], 1e-6)[:, None]
    nrm = np.c_[tang[:, 1], -tang[:, 0]] if outward is None else outward(base)
    paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeCap=skia.Paint.kRound_Cap)
    for k in range(n):
        ang = rng.normal(0, angle_jitter)
        ca, sa = math.cos(ang), math.sin(ang)
        d = np.array([nrm[k, 0]*ca - nrm[k, 1]*sa, nrm[k, 0]*sa + nrm[k, 1]*ca])
        ln = length*rng.uniform(0.5, 1.15)
        p0 = base[k] - d*ln*0.35; p2 = base[k] + d*ln
        bend = np.array([-d[1], d[0]])*rng.normal(0, ln*0.25)
        p1 = (p0 + p2)/2 + bend
        kk = rng.uniform(0.65, 1.25)
        paint.setColor4f(skia.Color4f(min(color.fR*kk, 1), min(color.fG*kk, 1), min(color.fB*kk, 1), 0.92))
        paint.setStrokeWidth(width*rng.uniform(0.6, 1.3))
        path = skia.Path(); path.moveTo(*p0); path.quadTo(p1[0], p1[1], p2[0], p2[1])
        canvas.drawPath(path, paint)

def ellipse_path(cx, cy, rx, ry):
    p = skia.Path(); p.addOval(skia.Rect(cx-rx, cy-ry, cx+rx, cy+ry)); return p

# ---------------------------------------------------------------------------------------------
class Character:
    """Opis wyglądu lalki (oryginalny projekt). Wymiary w px przy skali 1."""
    def __init__(self, name, skin, head_w=125, head_h=105, head_n=2.5, head_y=-300, jaw_squash=1.0,
                 mouth_y=22, mouth_w=0.86, mouth_smile=8, jaw_drop=58, lip_lift=16, inside='#3a0d14', tongue='#c2475a',
                 eye_r=31, eye_dx=46, eye_y=-88, pupil_r=10.5, lid_color=None, lid=0.25, eye_white='#f6f4ee',
                 nose=None, nose_r=(30, 25), nose_y=-22, brows=None, brow_y=-128, brow_len=58, brow_w=15,
                 hair=None, hair_style='tuft', hair_len=34, hair_seed=3,
                 torso_w=(92, 118), torso_h=190, costume=None, arm_len=(105, 100), arm_w=40, hand='#000000', rods=True,
                 scale=1.0, extra=None, seed=1):
        self.name = name; self.skin = Material(skin, 'felt', 0.55, seed=seed)
        self.skin_c = col(skin)
        self.head_w, self.head_h, self.head_n, self.head_y = head_w, head_h, head_n, head_y
        self.jaw_squash = jaw_squash
        self.mouth_y, self.mouth_w, self.mouth_smile, self.jaw_drop, self.lip_lift = mouth_y, mouth_w, mouth_smile, jaw_drop, lip_lift
        self.inside, self.tongue = col(inside), col(tongue)
        self.eye_r, self.eye_dx, self.eye_y, self.pupil_r = eye_r, eye_dx, eye_y, pupil_r
        self.lid_c = col(lid_color) if lid_color else shade(self.skin_c, 0.82); self.lid = lid
        self.eye_white = col(eye_white)
        self.nose = col(nose) if nose else None; self.nose_r, self.nose_y = nose_r, nose_y
        self.brows = col(brows) if brows else None; self.brow_y, self.brow_len, self.brow_w = brow_y, brow_len, brow_w
        self.hair = col(hair) if hair else None; self.hair_style, self.hair_len, self.hair_seed = hair_style, hair_len, hair_seed
        self.torso_w, self.torso_h = torso_w, torso_h
        self.costume = costume or {}
        self.arm_len, self.arm_w = arm_len, arm_w
        self.hand_c = col(hand) if hand != '#000000' else self.skin_c
        self.rods = rods; self.scale = scale; self.extra = extra or {}
        self.seed = seed
        # kształt głowy: superelipsa sparametryzowana kątem; usta przecinają obrys dokładnie w kącikach
        n = head_n
        yr = min(mouth_y/(head_h*(jaw_squash if mouth_y > 0 else 1)), 0.95)
        s_ = abs(yr)**(n/2)
        self.th_r = math.asin(min(s_, 0.999)) * (1 if mouth_y >= 0 else -1)
        self.th_l = math.pi - self.th_r
        self.mw = self._P(np.array([self.th_r]))[0, 0]          # połowa szerokości ust = szerokość głowy na wys. ust
        xs = np.linspace(-self.mw, self.mw, 31)
        self.mouth_curve = np.c_[xs, mouth_y + mouth_smile*(1 - (xs/self.mw)**2)]   # uśmiech: środek niżej niż kąciki
        self.up_arc = self._P(np.linspace(self.th_l, self.th_r + 2*np.pi, 90))       # przez czubek głowy
        self.lo_arc = self._P(np.linspace(self.th_r, self.th_l, 60))                 # przez brodę

    def _P(self, th):
        n = self.head_n; c, s = np.cos(th), np.sin(th)
        x = self.head_w*np.sign(c)*np.abs(c)**(2/n); y = self.head_h*np.sign(s)*np.abs(s)**(2/n)
        y = np.where(y > 0, y*self.jaw_squash, y)
        return np.c_[x, y]

    def head_paths(self, o, smile, rnd=0.0):
        mw = self.mw
        # rnd: zaokrąglenie ust (samogłoski o/u) - otwarcie skupione w środku, kąciki prawie zamknięte
        def prof(x, k):
            u = np.clip(np.abs(x)/mw, 0, 1)
            return (1 - rnd)*(1 - k*u**2) + rnd*np.clip(1 - (u/0.6)**2, 0, 1)**0.75
        def dl(x): return o*self.jaw_drop*prof(x, 0.8)
        def du(x): return -o*self.lip_lift*prof(x, 0.55)*(1 + 0.4*rnd)
        mc = self.mouth_curve.copy()
        mc[:, 1] -= smile*12*(np.abs(mc[:, 0])/mw)**3           # wyuczony uśmiech: kąciki w górę
        ul = mc + np.c_[np.zeros(len(mc)), du(mc[:, 0])]
        ll = mc + np.c_[np.zeros(len(mc)), dl(mc[:, 0])]
        ua = self.up_arc.copy(); ua[:, 1] += du(ua[:, 0])*np.clip((ua[:, 1] - (self.mouth_y - 60))/60, 0, 1)
        la = self.lo_arc.copy(); la[:, 1] += dl(la[:, 0])*0.95
        top = np.vstack([ua, ul[::-1][1:-1]])          # obrys góry (lewy kącik -> czubek -> prawy) + warga górna (prawa -> lewa)
        bot = np.vstack([la, ll[1:-1]])                # obrys żuchwy (prawy -> broda -> lewy) + warga dolna (lewa -> prawa)
        cav = np.vstack([ul, ll[::-1]])
        return top, bot, cav, ul, ll

    # -----------------------------------------------------------------------------------------
    def draw(self, cv, pose, light=1.0):
        """pose: mouth, smile, turn(-1..1), tilt(deg), nod(px), lean(deg), bob(px), gaze(x,y), blink, lid, brow(-1..1),
        hands: {'L':(x,y),'R':(x,y)} w ukł. lokalnym (względem pasa), props: lista funkcji rysujących w dłoni"""
        s = self.scale
        cv.save(); cv.scale(s, s)
        lean = pose.get('lean', 0.0); bob = pose.get('bob', 0.0)
        cv.translate(0, bob); cv.rotate(lean)
        self._draw_body(cv, pose)
        # głowa
        cv.save()
        nx, ny = 0, -self.torso_h - 8
        cv.translate(nx, ny + pose.get('nod', 0.0)); cv.rotate(pose.get('tilt', 0.0)); cv.translate(-nx, -ny)
        cv.translate(0, self.head_y)
        self._draw_head(cv, pose)
        cv.restore()
        self._draw_arms(cv, pose, front=True)
        cv.restore()

    def _draw_body(self, cv, pose):
        w0, w1 = self.torso_w; h = self.torso_h
        sh = 26   # zaokrąglenie barków
        body = np.array([[-w0, 40], [-w0*1.02, -h*0.45], [-w1, -h + sh], [-w1 + sh*0.6, -h + 4], [-w1*0.35, -h - 6], [0, -h - 8],
                         [w1*0.35, -h - 6], [w1 - sh*0.6, -h + 4], [w1, -h + sh], [w0*1.02, -h*0.45], [w0, 40]])
        self._draw_arms(cv, pose, front=False)
        c = dict(self.costume); c.update(pose.get('costume', {}))
        jacket = Material(c.get('jacket', '#6d6f78'), c.get('jacket_tex', 'felt'), 0.7, seed=self.seed + 7)
        bp = poly_path(body, True, True)
        fill(cv, bp, jacket)
        if c.get('shirt'):
            v = np.array([[-w1*0.38, -h - 4], [0, -h*0.38], [w1*0.38, -h - 4], [0, -h - 8]])
            fill(cv, poly_path(v, True, False), Material(c['shirt'], 'felt', 0.8, light=1.08, dark=0.9, seed=self.seed + 9))
        if c.get('tie'):
            t = np.array([[-9, -h + 6], [9, -h + 6], [6, -h + 22], [17, -h*0.42], [0, -h*0.30], [-17, -h*0.42], [-6, -h + 22]])
            fill(cv, poly_path(t, True, False), Material(c['tie'], 'felt', 0.8, seed=self.seed + 11))
        if c.get('lapels'):
            lc = Material(shade(col(c.get('jacket', '#6d6f78')), 0.8), 'felt', 0.7, seed=self.seed + 13)
            for sgn in (-1, 1):
                L = np.array([[sgn*w1*0.38, -h - 4], [sgn*w1*0.62, -h + 10], [sgn*w1*0.30, -h*0.55], [sgn*w1*0.05, -h*0.34]])
                fill(cv, poly_path(L, True, False), lc)
        if c.get('buttons'):
            p = skia.Paint(AntiAlias=True, Color4f=col(c['buttons']))
            for yy in (-h*0.24, -h*0.08): cv.drawCircle(0, yy, 6, p)
        if c.get('badge'):
            c['badge'](cv, w1, h)
        soft_edge(cv, bp, shade(col(c.get('jacket', '#6d6f78')), 0.5), 4, 0.4)


    def _arm_geom(self, pose, side):
        sgn = -1 if side == 'L' else 1
        w1 = self.torso_w[1]; h = self.torso_h
        sx, sy = sgn*(w1 - 18), -h + 34
        hx, hy = pose.get('hands', {}).get(side, (sgn*(w1 + 30), -30))
        L = self.arm_len[0] + self.arm_len[1]
        d = math.hypot(hx - sx, hy - sy)
        if d > L*0.98:                       # ręka nie może się rozciągnąć: dłoń dociągnięta do zasięgu
            k = L*0.98/d; hx, hy = sx + (hx - sx)*k, sy + (hy - sy)*k; d = L*0.98
        slack = math.sqrt(max(L*L - d*d, 0))*0.5
        mx, my = (sx + hx)/2, (sy + hy)/2
        ex, ey = mx + sgn*slack*0.45, my + slack*0.55     # miękki rękaw zwisa na zewnątrz i w dół
        return (sx, sy), (ex, ey), (hx, hy)

    def _draw_arms(self, cv, pose, front):
        for side in ('L', 'R'):
            infront = pose.get('arm_front', {}).get(side, True)
            if infront != front: continue
            (sx, sy), (ex, ey), (hx, hy) = self._arm_geom(pose, side)
            cc = dict(self.costume); cc.update(pose.get('costume', {}))
            sleeve = col(cc.get('sleeve', cc.get('jacket', '#6d6f78')))
            # pręt (rod): od dłoni w dół, poza kadr (zasłonięty krawędzią sceny)
            if self.rods:
                rp = skia.Paint(AntiAlias=True, StrokeWidth=3.2, Color4f=skia.Color4f(0.12, 0.11, 0.1, 0.95), Style=skia.Paint.kStroke_Style)
                cv.drawLine(hx, hy, hx + pose.get('rod_dx', {}).get(side, 0) + (12 if side == 'R' else -12), 420, rp)
            path = skia.Path(); path.moveTo(sx, sy); path.quadTo(ex, ey, hx, hy)
            p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=self.arm_w, StrokeCap=skia.Paint.kRound_Cap)
            m = Material(sleeve, 'felt', 0.7, seed=self.seed + 31)
            b = (min(sx, hx) - 30, min(sy, hy) - 30, max(sx, hx) + 30, max(sy, hy) + 30)
            p.setShader(m.paint(b).getShader())
            cv.drawPath(path, p)
            tp = m.tex_paint()
            if tp is not None:
                p2 = skia.Paint(tp); p2.setStyle(skia.Paint.kStroke_Style); p2.setStrokeWidth(self.arm_w); p2.setStrokeCap(skia.Paint.kRound_Cap)
                cv.drawPath(path, p2)
            # mankiet + dłoń (rękawiczka z kciukiem)
            ang = math.degrees(math.atan2(hy - ey, hx - ex))
            cv.save(); cv.translate(hx, hy); cv.rotate(ang - 90)
            hp = skia.Path(); hp.addRRect(skia.RRect.MakeRectXY(skia.Rect(-20, -4, 20, 34), 18, 18))
            th = skia.Path(); th.addRRect(skia.RRect.MakeRectXY(skia.Rect(-28 if side == 'R' else 12, 4, -10 if side == 'R' else 28, 18), 8, 8))
            hm = Material(self.hand_c, 'felt', 0.55, seed=self.seed + 41)
            fill(cv, th, hm); fill(cv, hp, hm)
            soft_edge(cv, hp, shade(self.hand_c, 0.5), 2.5, 0.35)
            cv.rotate(-(ang - 90))
            for prop in pose.get('props', {}).get(side, []):
                prop(cv)
            cv.restore()

    def _draw_head(self, cv, pose):
        o = float(np.clip(pose.get('mouth', 0.0), 0, 1.15)); smile = pose.get('smile', 0.0)
        turn = pose.get('turn', 0.0)
        top, bot, cav, ul, ll = self.head_paths(o, smile, float(np.clip(pose.get('round', 0.0), 0, 1)))
        fx = turn*self.head_w*0.22          # przesunięcie elementów twarzy przy obrocie głowy
        # włosy z tyłu
        if self.hair is not None and self.hair_style in ('long', 'bob'):
            self._draw_hair(cv, back=True, turn=turn)
        # cień rzucany przez głowę na tułów
        shp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.28)); shp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
        cv.drawOval(skia.Rect(-self.head_w*0.8, self.head_h*0.55, self.head_w*0.8, self.head_h*1.25), shp)
        # żuchwa
        bp = poly_path(bot, True, True); fill(cv, bp, self.skin)
        if self.extra.get('stubble'):
            if not hasattr(self, '_stub'):
                rng = np.random.default_rng(self.seed + 5); self._stub = rng.uniform([-1, 0], [1, 1], (420, 2))
            sc = col(self.extra['stubble'], 0.55); spp = skia.Paint(AntiAlias=True, Color4f=sc)
            cv.save(); cv.clipPath(bp, doAntiAlias=True)
            jd = o*self.jaw_drop
            for (u, v) in self._stub:
                x = u*self.mw*0.98; y = self.mouth_y + 14 + v*(self.head_h*self.jaw_squash - self.mouth_y) + jd*(1 - 0.8*u*u)
                cv.drawCircle(x, y, 1.6, spp)
            cv.restore()
        # wnętrze ust (rysowane po żuchwie, przed głową)
        if o > 0.01:
            cp = poly_path(cav, True, True)
            g = skia.GradientShader.MakeLinear([skia.Point(0, ul[:, 1].min()), skia.Point(0, ll[:, 1].max())], [shade(self.inside, 0.6).toColor(), self.inside.toColor()])
            pp = skia.Paint(AntiAlias=True); pp.setShader(g); cv.drawPath(cp, pp)
            # język
            cy = ll[:, 1].max() - 6
            tw = self.head_w*self.mouth_w*0.5
            cv.save(); cv.clipPath(cp, doAntiAlias=True)
            tp = skia.Paint(AntiAlias=True, Color4f=self.tongue); cv.drawOval(skia.Rect(-tw + fx*0.5, cy - 16*o - 6, tw + fx*0.5, cy + 22), tp)
            cv.restore()
        tp_ = poly_path(top, True, True); fill(cv, tp_, self.skin)
        # krawędzie warg (ciemniejszy filc)
        lp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=4.5, StrokeCap=skia.Paint.kRound_Cap,
                        Color4f=shade(self.skin_c, 0.62))
        cv.drawPath(poly_path(ul, False, True), lp)
        if o > 0.03: cv.drawPath(poly_path(ll, False, True), lp)
        soft_edge(cv, tp_, shade(self.skin_c, 0.45), 5, 0.35); soft_edge(cv, bp, shade(self.skin_c, 0.45), 5, 0.3)
        lift = -o*self.lip_lift*0.5
        if self.hair is not None:
            cv.save(); cv.translate(fx*0.4, lift); self._draw_hair(cv, back=False, turn=turn); cv.restore()
        cv.save(); cv.translate(fx, lift)
        if self.extra.get('cheeks'):
            cp_ = skia.Paint(AntiAlias=True, Color4f=col(self.extra['cheeks'], 0.35)); cp_.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 9))
            for sg in (-1, 1): cv.drawCircle(sg*self.head_w*0.55, self.nose_y + 10, 20, cp_)
        if self.nose is not None: self._draw_nose(cv)
        self._draw_eyes(cv, pose)
        if self.brows is not None: self._draw_brows(cv, pose)
        cv.restore()
        if self.extra.get('glasses'):
            cv.save(); cv.translate(fx, lift); self.extra['glasses'](cv, self); cv.restore()

    def _draw_nose(self, cv):
        rx, ry = self.nose_r; cy = self.nose_y
        g = skia.GradientShader.MakeRadial(skia.Point(-rx*0.35, cy - ry*0.4), rx*1.4,
                                           [shade(self.nose, 1.35).toColor(), self.nose.toColor(), shade(self.nose, 0.6).toColor()], [0, 0.5, 1])
        p = skia.Paint(AntiAlias=True); p.setShader(g)
        sp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.3)); sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
        cv.drawOval(skia.Rect(-rx*0.9, cy - ry*0.6 + 8, rx*0.9, cy + ry + 8), sp)
        cv.drawOval(skia.Rect(-rx, cy - ry, rx, cy + ry), p)

    def _draw_eyes(self, cv, pose):
        gx, gy = pose.get('gaze', (0.0, 0.0)); blink = pose.get('blink', 0.0); lid = max(pose.get('lid', self.lid), blink)
        r = self.eye_r
        for sg in (-1, 1):
            cx, cy = sg*self.eye_dx, self.eye_y
            sp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.35)); sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 5))
            cv.drawCircle(cx + 3, cy + 6, r, sp)
            g = skia.GradientShader.MakeRadial(skia.Point(cx - r*0.35, cy - r*0.4), r*1.5,
                                               [skia.Color4f(1, 1, 1, 1).toColor(), self.eye_white.toColor(), shade(self.eye_white, 0.72).toColor()], [0, 0.45, 1])
            p = skia.Paint(AntiAlias=True); p.setShader(g); cv.drawCircle(cx, cy, r, p)
            px, py = cx + gx*r*0.42, cy + gy*r*0.38
            cv.save(); cv.clipPath(ellipse_path(cx, cy, r, r), doAntiAlias=True)
            pp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.05, 0.04, 0.05, 1)); cv.drawCircle(px, py, self.pupil_r, pp)
            # powieka (filc) - zakrywa górną część kulki
            if lid > 0.02:
                ly = cy - r + 2*r*min(lid, 1.0)
                lp = skia.Path(); lp.addRect(skia.Rect(cx - r - 2, cy - r - 2, cx + r + 2, ly))
                fill(cv, lp, Material(self.lid_c, 'felt', 0.5, seed=self.seed + 51))
                ep = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color4f=shade(self.lid_c, 0.55))
                cv.drawLine(cx - r, ly, cx + r, ly, ep)
            cv.restore()
            hp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.85)); cv.drawCircle(cx - r*0.38, cy - r*0.42, r*0.13, hp)

    def _draw_brows(self, cv, pose):
        b = pose.get('brow', 0.0)
        for sg in (-1, 1):
            cv.save(); cv.translate(sg*self.eye_dx, self.brow_y - b*10)
            cv.rotate(sg*(-b*12 + 4))
            p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect(-self.brow_len/2, -self.brow_w/2, self.brow_len/2, self.brow_w/2), self.brow_w/2, self.brow_w/2))
            fill(cv, p, Material(self.brows, 'felt', 0.5, seed=self.seed + 61))
            cv.restore()

    def _draw_hair(self, cv, back, turn):
        # futro jest statyczne względem głowy -> nagrywane raz do skia.Picture i odtwarzane (szybko)
        if not hasattr(self, '_pics'): self._pics = {}
        key = ('hair', back)
        if key not in self._pics:
            rec = skia.PictureRecorder()
            c2 = rec.beginRecording(skia.Rect(-600, -600, 600, 600))
            self._draw_hair_raw(c2, back)
            self._pics[key] = rec.finishRecordingAsPicture()
        cv.drawPicture(self._pics[key])

    def _draw_hair_raw(self, cv, back):
        hw, hh = self.head_w, self.head_h
        st = self.hair_style
        if st == 'tuft' and not back:
            arc = superellipse(hw*0.7, hh*0.95, 2.2, 60)
            arc = arc[(arc[:, 1] < -hh*0.62)]
            arc = arc[np.argsort(arc[:, 0])]
            fur_fringe(cv, arc, self.hair, self.hair_len, 1.6, self.hair_seed, 0.45, 4.0, outward=lambda P: np.c_[P[:, 0]/max(hw, 1)*0.6, -np.ones(len(P))]/np.hypot(P[:, 0]/max(hw, 1)*0.6, 1)[:, None])
        elif st == 'shag':
            arc = superellipse(hw*1.02, hh*1.02, 2.3, 90)
            arc = arc[arc[:, 1] < (hh*0.1 if back else -hh*0.35)]
            arc = arc[np.argsort(np.arctan2(arc[:, 1], arc[:, 0]))]
            fur_fringe(cv, arc, self.hair, self.hair_len*(1.3 if back else 1.0), 2.0, self.hair_seed + (0 if back else 5), 0.6, 4.5,
                       outward=lambda P: P/np.hypot(P[:, 0], P[:, 1])[:, None])
        elif st in ('long', 'bob'):
            if back:
                L = 1.55 if st == 'long' else 1.05
                pts = np.array([[-hw*1.08, -hh*0.2], [-hw*1.15, hh*L*0.6], [-hw*0.9, hh*L], [-hw*0.4, hh*L*0.9], [hw*0.4, hh*L*0.9],
                                [hw*0.9, hh*L], [hw*1.15, hh*L*0.6], [hw*1.08, -hh*0.2], [hw*0.7, -hh*1.05], [0, -hh*1.18], [-hw*0.7, -hh*1.05]])
                fill(cv, poly_path(pts), Material(self.hair, 'felt', 0.5, light=1.25, dark=0.6, seed=self.hair_seed))
                fur_fringe(cv, pts, self.hair, 16, 0.8, self.hair_seed + 3, 0.4, 3.0, outward=lambda P: P/np.hypot(P[:, 0], P[:, 1] - 0.3*hh)[:, None])
            else:
                pts = np.array([[-hw*1.05, -hh*0.25], [-hw*0.95, -hh*0.8], [-hw*0.5, -hh*1.12], [hw*0.2, -hh*1.15], [hw*0.85, -hh*0.95],
                                [hw*1.06, -hh*0.3], [hw*0.7, -hh*0.62], [hw*0.1, -hh*0.72], [-hw*0.45, -hh*0.62], [-hw*0.85, -hh*0.4]])
                fill(cv, poly_path(pts), Material(self.hair, 'felt', 0.5, light=1.25, dark=0.65, seed=self.hair_seed + 1))
                fur_fringe(cv, pts[:6], self.hair, 14, 0.9, self.hair_seed + 4, 0.35, 3.0, outward=lambda P: P/np.hypot(P[:, 0], P[:, 1])[:, None])
        elif st == 'combover' and not back:   # zaczeska: pasma zaczesane z boku na czubek
            pts = np.array([[-hw*0.95, -hh*0.55], [-hw*0.7, -hh*0.92], [-hw*0.1, -hh*1.08], [hw*0.55, -hh*1.0], [hw*0.92, -hh*0.62],
                            [hw*0.7, -hh*0.78], [hw*0.1, -hh*0.86], [-hw*0.5, -hh*0.74]])
            fill(cv, poly_path(pts), Material(self.hair, 'felt', 0.5, light=1.3, dark=0.7, seed=self.hair_seed))
            rng = np.random.default_rng(self.hair_seed)
            lp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeCap=skia.Paint.kRound_Cap)
            for k in range(46):
                y0 = -hh*rng.uniform(0.6, 0.98); x0 = -hw*rng.uniform(0.6, 0.95)
                pa = skia.Path(); pa.moveTo(x0, y0); pa.cubicTo(x0 + hw*0.5, y0 - hh*0.35, x0 + hw*1.2, y0 - hh*0.2, x0 + hw*rng.uniform(1.3, 1.8), y0 + hh*0.1)
                kk = rng.uniform(0.7, 1.4); lp.setColor4f(shade(self.hair, kk)); lp.setStrokeWidth(rng.uniform(2, 4.5)); cv.drawPath(pa, lp)
            fur_fringe(cv, pts[:5], self.hair, 12, 0.7, self.hair_seed + 2, 0.4, 2.6, outward=lambda P: P/np.hypot(P[:, 0], P[:, 1])[:, None])
        elif st == 'ring' and not back:     # wianuszek włosów wokół łysiny
            for sg in (-1, 1):
                arc = superellipse(hw*1.0, hh*1.0, 2.3, 80)
                arc = arc[(arc[:, 0]*sg > hw*0.55) & (arc[:, 1] < hh*0.05) & (arc[:, 1] > -hh*0.75)]
                fur_fringe(cv, arc, self.hair, self.hair_len, 2.2, self.hair_seed + (sg > 0), 0.5, 4.0, outward=lambda P: P/np.hypot(P[:, 0], P[:, 1])[:, None])
