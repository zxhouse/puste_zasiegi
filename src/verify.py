"""Weryfikacja gotowego pliku. Wyniki: checks/verify.json + checks/*.png. Użycie: python3 verify.py <plik.mp4> [--quick]"""
import os, sys, json, subprocess, unicodedata, math, argparse
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video'))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument('mp4'); ap.add_argument('--quick', action='store_true'); ap.add_argument('--out', default=os.path.join(ROOT, 'checks'))
A = ap.parse_args()
OUT = A.out; os.makedirs(OUT, exist_ok=True)
R = {}
def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)

# ---------------------------------------------------------------- 1. dekodowanie i parametry
r = run(['ffmpeg', '-v', 'error', '-i', A.mp4, '-f', 'null', '-'])
R['decode_errors'] = r.stderr.strip().splitlines()[:20]
pr = json.loads(run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', A.mp4]).stdout)
vs = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]; au = [s for s in pr['streams'] if s['codec_type'] == 'audio'][0]
R['video'] = dict(codec=vs['codec_name'], profile=vs.get('profile'), pix_fmt=vs['pix_fmt'], size=f"{vs['width']}x{vs['height']}", r_frame_rate=vs['r_frame_rate'],
                  nb_read_frames=int(vs['nb_read_frames']), duration=float(vs['duration']))
R['audio'] = dict(codec=au['codec_name'], sample_rate=int(au['sample_rate']), channels=au['channels'], duration=float(au['duration']), bit_rate=au.get('bit_rate'))
R['format'] = dict(duration=float(pr['format']['duration']), size_MB=round(int(pr['format']['size'])/1e6, 2), tags=pr['format'].get('tags', {}))
import engine as E
R['expected_frames'] = E.N_FRAMES
# ---------------------------------------------------------------- 2. dźwięk: przesunięcie 0 próbek (korelacja w kilku miejscach)
song = [os.path.join(ROOT, f) for f in os.listdir(ROOT) if unicodedata.normalize('NFC', f).startswith('Puste zasięgi') and f.endswith('.mp3')][0]
tmpa = os.path.join(OUT, '_a_orig.wav'); tmpb = os.path.join(OUT, '_a_mp4.wav')
run(['ffmpeg', '-v', 'error', '-y', '-i', song, '-map', '0:a:0', '-c:a', 'pcm_f32le', tmpa])
run(['ffmpeg', '-v', 'error', '-y', '-i', A.mp4, '-map', '0:a:0', '-c:a', 'pcm_f32le', tmpb])
xa, sra = sf.read(tmpa); xb, srb = sf.read(tmpb)
xa = xa.mean(1); xb = xb.mean(1)
offs = []
for c in [5.0, 30.0, 61.0, 100.0, 140.0, 170.0, 200.0, 210.0]:
    n = int(1.5*sra); a0 = int(c*sra)
    seg = xa[a0:a0 + n]; L = 2400
    best = None
    for lag in range(-L, L + 1, 1) if False else []: pass
    # korelacja przez FFT w oknie ±L próbek
    win = xb[a0 - L:a0 + n + L]
    cc = np.correlate(win, seg, 'valid'); lag = int(np.argmax(cc)) - L
    rho = float(np.dot(seg, xb[a0 + lag:a0 + lag + n])/(np.linalg.norm(seg)*np.linalg.norm(xb[a0 + lag:a0 + lag + n]) + 1e-12))
    offs.append(dict(at_s=c, lag_samples=lag, corr=round(rho, 6)))
R['audio_offset'] = offs
R['audio_samples'] = dict(original=len(xa), in_mp4=len(xb), diff=len(xb) - len(xa))
m = min(len(xa), len(xb)); d = xa[:m] - xb[:m]
R['audio_snr_db'] = round(float(10*np.log10((xa[:m]**2).sum()/((d**2).sum() + 1e-20))), 2)
os.remove(tmpa); os.remove(tmpb)
print(json.dumps({k: R[k] for k in ('decode_errors', 'video', 'audio', 'format', 'audio_offset', 'audio_samples', 'audio_snr_db')}, ensure_ascii=False, indent=1))
json.dump(R, open(os.path.join(OUT, 'verify_file.json'), 'w'), ensure_ascii=False, indent=1)
if A.quick: sys.exit(0)

# ---------------------------------------------------------------- 3. arkusze klatek co 4 s + stopklatki
sheets = os.path.join(OUT, 'sheets'); os.makedirs(sheets, exist_ok=True)
run(['ffmpeg', '-v', 'error', '-y', '-i', A.mp4, '-vf', "fps=1/4,scale=384:-1,drawtext=fontfile=" + os.path.join(ROOT, 'fonts/inter/Inter-SemiBold.otf') +
     ":text='%{pts\\:hms}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,tile=5x6", os.path.join(sheets, 'sheet_%02d.png')])
stills = os.path.join(OUT, 'stills'); os.makedirs(stills, exist_ok=True)
KEY = {'intro_mowa': 5.0, 'kawa': 15.1, 'garnitur': 18.5, 'szczeka': 22.7, 'przyjemnosc': 23.9, 'feed_tak_tak': 28.6, 'awans': 34.2, 'strategiczny_gest': 38.2,
       'konferencja_flesz': 40.0, 'szacun': 44.5, 'usmiech_wyuczony': 51.2, 'wielki_gest': 58.4, 'refren1': 61.0, 'peka': 65.9, 'pod_spodem': 71.5, 'hej': 75.5,
       'feed_grazyna': 81.5, 'cringe': 85.9, 'piec_scenek': 88.0, 'nowa_droga': 91.0, 'bruk': 96.8, 'wywalili': 100.8, 'case_study': 104.4, 'trzy_opinie': 108.3,
       'swiety': 113.5, 'studio_w_drewnie': 120.4, 'refren2': 129.5, 'maski_pekaja': 135.0, 'analityka': 137.0, 'brak_komentarzy': 140.0, 'bridge_szczerze': 149.5,
       'robie_swoje': 158.7, 'fanfary': 162.7, 'prosty_wpis': 165.6, 'refren3': 169.0, 'cisza_razem': 179.0, 'dziekuje': 189.3, 'scrollowanie': 192.0,
       'final': 197.0, 'statystyki': 205.8, 'hej_koniec': 209.9, 'napisy': 214.0}
for k, t in KEY.items():
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', A.mp4, '-frames:v', '1', os.path.join(stills, f'{t:07.2f}_{k}.png')])
print('sheets & stills written')
