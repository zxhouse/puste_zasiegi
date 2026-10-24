"""Render całego teledysku: kawałki po CHUNK klatek renderowane równolegle (każda klatka niezależna od pozostałych),
potem sklejenie (concat, bez rekompresji) i dołożenie dźwięku z oryginalnego MP3.
Użycie: python3 render_all.py <katalog_wyjściowy_kawałków> [--jobs 4] [--chunk 300]"""
import os, sys, subprocess, time, argparse, glob
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video'))
import engine as E
ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--jobs', type=int, default=4); ap.add_argument('--chunk', type=int, default=300)
ap.add_argument('--only', default=None, help='lista indeksów kawałków do (ponownego) renderu, np. 3,7')
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
N = E.N_FRAMES
chunks = [(i, s, min(s + a.chunk, N)) for i, s in enumerate(range(0, N, a.chunk))]
if a.only: chunks = [c for c in chunks if str(c[0]) in a.only.split(',')]
def run(c):
    i, s, e = c
    out = os.path.join(a.out, f'chunk_{i:03d}.mp4')
    if os.path.exists(out) and not a.only: return f'skip {i}'
    tmp = out + '.part.mp4'
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'video', 'render.py'), str(s), str(e), tmp],
                       capture_output=True, text=True)
    if r.returncode != 0: return f'FAIL {i}: {r.stderr[-2000:]}'
    os.replace(tmp, out)
    return f'chunk {i} ({s}-{e}) {time.time() - t0:.0f}s'
t0 = time.time()
with ThreadPoolExecutor(a.jobs) as ex:
    for msg in ex.map(run, chunks):
        print(msg, f'[{time.time() - t0:.0f}s]', flush=True)
print('all chunks done', f'{time.time() - t0:.0f}s')
