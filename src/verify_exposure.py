"""Ekspozycja gotowego pliku: dla każdej klatki (10 kl./s, 480×270) średnia luma, odsetek pikseli przepalonych
(kanał ≥ 250) i bardzo jasnych (luma ≥ 235), osobno dla ujęć sceny i przebitek do serwisu (strona serwisu jest z natury
biała - liczy się tylko scena). Porównanie z v3 (archive/v3/exposure_v3.json). Wynik: checks/exposure.json
Użycie: python3 verify_exposure.py final/music-video.mp4"""
import os, sys, json, subprocess, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video'))
import engine as E, timeline as T
ROOT = E.ROOT; W, H = 480, 270
def measure(path):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'fps=10,scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    out = []; i = 0
    while True:
        b = p.stdout.read(W*H*3)
        if len(b) < W*H*3: break
        a = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32)
        y = 0.2126*a[..., 0] + 0.7152*a[..., 1] + 0.0722*a[..., 2]
        out.append((i/10, round(float(y.mean()), 1), round(float(np.mean(a.max(2) >= 250))*100, 2), round(float(np.mean(y >= 235))*100, 2), round(float(np.percentile(y, 99)), 1)))
        i += 1
    return out
def kinds_v3(n):
    """Rodzaj ujęcia w v3 (z kodu v3: build/v3/src) - żeby porównanie liczyło te same ujęcia sceny."""
    src = os.path.join(ROOT, 'build/v3/src/video')
    if not os.path.exists(src): return None
    code = ("import sys, json; sys.path.insert(0, %r); import timeline as T; "
            "print(json.dumps([T.shot_at(i/10 + 0.001)[2] for i in range(%d)]))" % (src, n))
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=src)
    return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else None
def summary(rows, kinds=None):
    st = [r for k, r in enumerate(rows) if (kinds[k] if kinds else T.shot_at(r[0] + 0.001)[2]) in ('stage', 'under') and r[0] < E.SONG_DUR]
    a = np.array([r[1:] for r in st])
    return dict(stage_frames=len(st), mean_luma=round(float(a[:, 0].mean()), 1), clip_pct_mean=round(float(a[:, 1].mean()), 2),
                clip_pct_p95=round(float(np.percentile(a[:, 1], 95)), 2), clip_pct_max=round(float(a[:, 1].max()), 2),
                frames_clip_over_5pct=int(np.sum(a[:, 1] > 5)), frames_clip_over_1pct=int(np.sum(a[:, 1] > 1)),
                p99_luma_median=round(float(np.median(a[:, 3])), 1), worst=[st[k][0] for k in np.argsort(-a[:, 1])[:5]])
rows = measure(sys.argv[1])
R = dict(v4=summary(rows))
v3p = os.path.join(ROOT, 'archive/v3/exposure_v3.json')
if os.path.exists(v3p):
    r3 = [tuple(r) for r in json.load(open(v3p))]
    R['v3_same_measure'] = summary(r3, kinds_v3(len(r3)))
R['note'] = ('ujęcia sceny i pod sceną; przebitki do serwisu pominięte (biała strona serwisu jest celowo jasna i bez obróbki); '
             'v3 liczone tą samą miarą na pliku z archive/v3, z podziałem na ujęcia z kodu v3')
os.makedirs(os.path.join(ROOT, 'checks'), exist_ok=True)
json.dump(R, open(os.path.join(ROOT, 'checks', 'exposure.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(R, ensure_ascii=False, indent=1))
