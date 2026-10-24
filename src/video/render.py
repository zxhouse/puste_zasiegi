"""Render klatek [a, b) -> ffmpeg (rawvideo RGBA -> H.264). Każda klatka liczona tylko z czasu t = i/30."""
import sys, os, subprocess, time, argparse
import numpy as np, skia
import engine as E
import timeline as T
import compose as CP
import under as U
import post
import linkedin as LI
import credits as CR

def render_frame(i, surf=None):
    t = i/E.FPS
    surf = surf or skia.Surface(E.W, E.H)
    cv = surf.getCanvas(); cv.resetMatrix()
    sc = T.scene_at(t)
    if sc['mode'] == 'stage':
        CP.render_stage(cv, sc, t)
    elif sc['mode'] == 'under':
        U.render_under(cv, t, sc['cam'], sc.get('variant', 'quiet'), sc.get('line', (4, 3)), sc.get('t0'))
    elif sc['mode'] == 'feed':
        LI.render_feed(cv, t, sc)
    else:
        CR.render_credits(cv, t, sc)
    if sc['mode'] == 'feed':
        pass        # strona serwisu jest czysta (bez ziarna, blasku, winiety); 'filmowa' obróbka siedzi tylko w obrazie filmu w poście
    elif sc['mode'] == 'credits':
        post.apply(surf, i, halation=0.3, grain=0.7)
    else:
        post.apply(surf, i)
        if sc['mode'] == 'stage': detune(surf, t)
    return surf

def detune(surf, t):
    """Fałszujący fragment (refren 2, 2:07-2:11): obraz 'rozstraja się' jak dźwięk - kanały R i B lekko się rozjeżdżają
    i falują (jak rozstrojony odbiornik), narasta i opada płynnie."""
    a0, a1 = T.lt(T.PRE2, 3) + 1.8, T.lt(T.CH2, 1)
    k = E.smoothstep((t - a0)/0.8)*(1 - E.smoothstep((t - (a1 - 0.25))/0.25))
    if k <= 0.01: return
    img = surf.makeImageSnapshot(); cv = surf.getCanvas(); cv.save(); cv.resetMatrix()
    d = k*(5 + 4*np.sin(t*2*np.pi*1.7)); wy = k*2*np.sin(t*2*np.pi*0.9)
    cv.clear(skia.Color4f(0, 0, 0, 1))
    for m, dx, dy in (([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0], d, wy), ([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0], 0, 0),
                      ([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0], -d, -wy)):
        p = skia.Paint(); p.setColorFilter(skia.ColorFilters.Matrix(m)); p.setBlendMode(skia.BlendMode.kPlus)
        cv.drawImage(img, float(dx), float(dy), skia.SamplingOptions(skia.FilterMode.kLinear), p)
    cv.restore()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('a', type=int); ap.add_argument('b', type=int); ap.add_argument('out')
    ap.add_argument('--png', action='store_true')
    a = ap.parse_args()
    surf = skia.Surface(E.W, E.H)
    if a.png:
        os.makedirs(a.out, exist_ok=True)
        for i in range(a.a, a.b):
            render_frame(i, surf).makeImageSnapshot().save(os.path.join(a.out, f'f{i:05d}.png'), skia.kPNG)
        return
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{E.W}x{E.H}', '-r', str(E.FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', '-g', '60', a.out], stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(a.a, a.b):
        render_frame(i, surf)
        arr = surf.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
        ff.stdin.write(arr.tobytes())
        if (i - a.a) % 60 == 0:
            print(f'[{a.a}-{a.b}] frame {i} {(time.time() - t0)/(i - a.a + 1):.2f}s/fr', flush=True)
    ff.stdin.close(); ff.wait()
    print(f'done {a.a}-{a.b} in {time.time() - t0:.0f}s', flush=True)

if __name__ == '__main__':
    main()
