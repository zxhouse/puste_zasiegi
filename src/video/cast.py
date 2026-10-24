"""Obsada - oryginalne lalki zaprojektowane do tego teledysku (bez odwołań do istniejących postaci)."""
import skia, numpy as np
from puppet import Character, col, shade, Material, fill, poly_path

def round_glasses(color='#2b2b2b', r=22, dx=46, dy=-88):
    def f(cv, ch):
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=col(color))
        for sg in (-1, 1): cv.drawCircle(sg*dx, dy, r, p)
        cv.drawLine(-dx + r, dy, dx - r, dy, p)
        g = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.12))
        for sg in (-1, 1): cv.drawCircle(sg*dx, dy, r - 3, g)
    return f

def star_shades(cv, ch):        # okulary-gwiazdy Grażyny (na czubku głowy)
    p = skia.Paint(AntiAlias=True, Color4f=col('#ff4fa0'))
    for sg in (-1, 1):
        pts = []
        for k in range(10):
            a = -np.pi/2 + k*np.pi/5; rr = 24 if k % 2 == 0 else 11
            pts.append((sg*42 + rr*np.cos(a), -ch.head_h*0.98 + rr*np.sin(a)))
        cv.drawPath(poly_path(pts, True, False), p)
    lp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=col('#ff4fa0')); cv.drawLine(-20, -ch.head_h*0.98, 20, -ch.head_h*0.98, lp)

def lanyard(text_col='#f2c94c'):
    def f(cv, w1, h):
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6, Color4f=col('#1d4e89'))
        path = skia.Path(); path.moveTo(-w1*0.3, -h); path.quadTo(0, -h*0.35, w1*0.3, -h); cv.drawPath(path, p)
        cv.drawRect(skia.Rect(-26, -h*0.45, 26, -h*0.18), skia.Paint(AntiAlias=True, Color4f=col('#ffffff')))
        cv.drawRect(skia.Rect(-26, -h*0.45, 26, -h*0.38), skia.Paint(AntiAlias=True, Color4f=col(text_col)))
    return f

HENIO = Character('Henio Kawka', '#d6b48c', head_w=128, head_h=104, head_n=2.9, jaw_squash=1.12, mouth_w=0.88, mouth_smile=6,
                  jaw_drop=62, eye_r=33, eye_dx=46, eye_y=-84, lid=0.38, nose='#a04a3a', nose_r=(30, 34), nose_y=-26,
                  brows='#3a2f2a', brow_y=-128, brow_len=58, brow_w=19, hair='#3b2a20', hair_style='combover', hair_len=30,
                  torso_w=(96, 122), costume=dict(jacket='#6f7480', shirt='#f1efe8', tie='#c0392b', lapels=True, buttons='#2f3238'),
                  extra=dict(stubble='#5a6170'), seed=11)

GRAZYNA = Character('Grażyna Gratka', '#b9a3e3', head_w=108, head_h=112, head_n=2.2, mouth_w=0.8, mouth_smile=9, jaw_drop=54,
                    eye_r=29, eye_dx=40, eye_y=-86, lid=0.12, nose='#9a78d6', nose_r=(18, 15), nose_y=-26, brows='#5b2c6f',
                    brow_len=48, brow_w=11, hair='#ff6fb5', hair_style='long', torso_w=(78, 104),
                    costume=dict(jacket='#e8e4da', lapels=True, shirt='#ff6fb5'), extra=dict(glasses=star_shades, cheeks='#ff6fb5'), seed=21)

PREZES = Character('Prezes Bogumił Łaskawiec', '#8e3f4a', head_w=150, head_h=108, head_n=2.1, jaw_squash=1.15, mouth_w=0.82, mouth_smile=4,
                   jaw_drop=60, eye_r=27, eye_dx=50, eye_y=-78, lid=0.3, nose='#6b2b35', nose_r=(36, 26), nose_y=-20,
                   brows='#e8e2d0', brow_len=56, brow_w=14, hair='#e8e2d0', hair_style='ring', hair_len=26, torso_w=(130, 150),
                   costume=dict(jacket='#1f2a44', shirt='#f5f2ea', tie='#d4a017', lapels=True, buttons='#d4a017'),
                   extra=dict(glasses=round_glasses('#d4a017', 24, 50, -78)), seed=31)

TADEK = Character('Tadek Nowadroga', '#8fc3e6', head_w=96, head_h=118, head_n=2.3, mouth_w=0.82, mouth_smile=5, jaw_drop=56,
                  eye_r=27, eye_dx=38, eye_y=-92, lid=0.3, nose='#5f9cc7', nose_r=(20, 24), nose_y=-30, brows='#3b4d61',
                  brow_len=44, brow_w=11, hair='#3b4d61', hair_style='tuft', hair_len=22, torso_w=(78, 96),
                  costume=dict(jacket='#7a9a5c', shirt='#f4f0e6', lapels=False), extra=dict(glasses=round_glasses('#2b2b2b', 21, 38, -92)), seed=41)

MIREK = Character('Mirek Szacun', '#5cc8b2', head_w=84, head_h=80, head_n=2.0, mouth_w=0.9, mouth_smile=7, jaw_drop=48,
                  eye_r=24, eye_dx=30, eye_y=-58, lid=0.05, nose=None, brows='#1f6f62', brow_len=30, brow_w=9, brow_y=-92,
                  hair='#5cc8b2', hair_style='shag', hair_len=20, torso_w=(58, 70), torso_h=120, head_y=-200,
                  costume=dict(jacket='#f6c945'), arm_len=(70, 66), arm_w=30, extra=dict(glasses=round_glasses('#d63c3c', 17, 30, -58)), seed=51)

KASIA = Character('Kasia Kejs', '#f2b48a', head_w=104, head_h=104, head_n=2.3, mouth_w=0.8, mouth_smile=8, jaw_drop=52,
                  eye_r=28, eye_dx=38, eye_y=-84, lid=0.15, nose='#d9825a', nose_r=(16, 14), nose_y=-26, brows='#1b2f5e',
                  brow_len=44, brow_w=11, hair='#1b2f5e', hair_style='bob', torso_w=(80, 100),
                  costume=dict(jacket='#e0563b', shirt='#fbf6ec'), extra=dict(glasses=round_glasses('#1b2f5e', 22, 40, -84), cheeks='#e0563b'), seed=61)

CHOIR_COLORS = [('#e4c65c', '#3d5a80', 'm'), ('#73b7a6', '#5a3e85', 'm'), ('#d98b7b', '#2f4858', 'm'), ('#9fa8da', '#7a4419', 'm'),
                ('#f2a1c0', '#2a9d8f', 'f'), ('#b5d66b', '#8e3b46', 'f'), ('#f4b860', '#3a506b', 'f'), ('#c1a1d3', '#b5523b', 'f')]
def choir_member(i):
    skin, jacket, g = CHOIR_COLORS[i]
    hair = ['#3b2b20', '#6b3e26', '#1e1e24', '#8a5a2b', '#d9480f', '#3f3d56', '#7b2d26', '#2b2d42'][i]
    return Character(f'Chór {i+1}', skin, head_w=74, head_h=70, head_n=2.3 if g == 'm' else 2.1, mouth_w=0.84, mouth_smile=6, jaw_drop=40,
                     eye_r=20, eye_dx=28, eye_y=-56, lid=0.18, nose=shade(col(skin), 0.75) if False else None, brows=hair, brow_len=28,
                     brow_w=8, brow_y=-84, hair=hair, hair_style='tuft' if g == 'm' else ['long', 'bob'][i % 2], hair_len=18,
                     torso_w=(54, 66), torso_h=118, head_y=-190, costume=dict(jacket=jacket, shirt='#f3efe6', tie=('#c0392b' if g == 'm' else None), lapels=(g == 'm')),
                     arm_len=(66, 60), arm_w=26, seed=100 + i*7)
CHOIR = [choir_member(i) for i in range(8)]
