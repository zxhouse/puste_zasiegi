"""Zasoby klonu serwisu generowane z renderera teledysku: awatary lalek, zdjęcia do wpisów, okładka filmu."""
import os, skia, numpy as np
import engine as E, cast as C, render as R
OUT = os.path.join(E.ROOT, 'linkedin_clone', 'assets'); os.makedirs(OUT, exist_ok=True)

def avatar(ch, name, bg, pose=None, zoom=1.0, dy=0.0):
    S = 400; surf = skia.Surface(S, S); cv = surf.getCanvas()
    g = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, S)], [skia.Color4f(*bg, 1).toColor(), skia.Color4f(bg[0]*0.75, bg[1]*0.75, bg[2]*0.75, 1).toColor()])
    p = skia.Paint(); p.setShader(g); cv.drawRect(skia.Rect(0, 0, S, S), p)
    k = 0.95*S/(2.9*ch.head_w*ch.scale)*zoom
    cv.translate(S/2, S*0.62 + dy); cv.scale(k, k); cv.translate(0, -(ch.head_y))
    ch.draw(cv, pose or dict(mouth=0.18, smile=0.8, gaze=(0.0, 0.05), hands={'L': (-150, 80), 'R': (150, 80)}, lid=min(ch.lid, 0.25)))
    surf.makeImageSnapshot().save(os.path.join(OUT, name + '.png'), skia.kPNG)

avatar(C.HENIO, 'av_henio', (0.55, 0.72, 0.86))
avatar(C.GRAZYNA, 'av_grazyna', (0.98, 0.84, 0.90))
avatar(C.PREZES, 'av_prezes', (0.82, 0.78, 0.66))
avatar(C.TADEK, 'av_tadek', (0.86, 0.93, 0.80))
avatar(C.MIREK, 'av_mirek', (1.0, 0.93, 0.70))
avatar(C.KASIA, 'av_kasia', (0.82, 0.90, 0.98))
for i in range(4): avatar(C.CHOIR[i], f'av_chor{i}', (0.9, 0.88, 0.95))

import timeline as T
def still(t, name, crop=None, w=1200):
    saved = list(T.SIGNS); T.SIGNS.clear()          # zdjęcia do wpisów bez tablic z tekstem piosenki
    surf = R.render_frame(int(round(t*E.FPS)))
    T.SIGNS.extend(saved)
    img = surf.makeImageSnapshot()
    if crop:
        x0, y0, x1, y1 = crop
        s2 = skia.Surface(int((x1 - x0)*w/(x1 - x0)), int((y1 - y0)*w/(x1 - x0))); c2 = s2.getCanvas()
        c2.drawImageRect(img, skia.Rect(x0, y0, x1, y1), skia.Rect(0, 0, s2.width(), s2.height()), skia.SamplingOptions(skia.FilterMode.kLinear))
        img = s2.makeImageSnapshot()
    img.save(os.path.join(OUT, name + '.jpg'), skia.kJPEG, 90)

still(84.5, 'img_grazyna')                 # studio Grażyny (zdjęcie we wpisie = kadr, w który wjeżdżamy)
still(40.6, 'img_konferencja')
still(104.6, 'img_kasia')
still(3.6, 'poster_video')                 # okładka filmu: kurtyna, Henio
print('ok')
