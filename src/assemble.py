"""Sklejenie kawałków + dźwięk: H.264 yuv420p 1920x1080 30 kl./s, AAC z całego MP3 (bez filtrów, bez cięcia).
Użycie: python3 assemble.py <katalog_kawałków> <plik.mp4> [--crf 20]"""
import os, sys, subprocess, glob, argparse, unicodedata
ap = argparse.ArgumentParser(); ap.add_argument('chunks'); ap.add_argument('out'); ap.add_argument('--crf', default='20'); ap.add_argument('--maxrate', default=None)
ap.add_argument('--vbitrate', default=None, help='kodowanie dwuprzebiegowe do zadanej przepływności (np. 3200k), by plik zmieścił się w limicie GitHuba 100 MB')
a = ap.parse_args()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
song = [os.path.join(ROOT, f) for f in os.listdir(ROOT) if unicodedata.normalize('NFC', f).startswith('Puste zasięgi') and f.endswith('.mp3')][0]
files = sorted(glob.glob(os.path.join(a.chunks, 'chunk_*.mp4')))
lst = os.path.join(a.chunks, 'list.txt')
open(lst, 'w').write(''.join(f"file '{os.path.abspath(f)}'\n" for f in files))
video_only = os.path.join(a.chunks, 'video_concat.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', video_only], check=True)
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
cmd = ['ffmpeg', '-v', 'error', '-y', '-i', video_only, '-i', song, '-map', '0:v:0', '-map', '1:a:0',
       '-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.1', '-r', '30',
       '-x264-params', 'keyint=60:min-keyint=30', '-c:a', 'aac', '-b:a', '320k',
       '-metadata', 'title=Puste zasięgi', '-metadata', 'artist=Paweł Kuraś', '-metadata', 'author=Paweł Kuraś',
       '-metadata', 'composer=Paweł Kuraś', '-metadata', 'comment=Teledysk: Paweł Kuraś', '-movflags', '+faststart', a.out]
if a.maxrate: cmd[cmd.index('-crf'):cmd.index('-crf') + 2] = ['-crf', a.crf, '-maxrate', a.maxrate, '-bufsize', str(int(a.maxrate.rstrip('k'))*2) + 'k']
if a.vbitrate:
    i = cmd.index('-crf'); cmd[i:i + 2] = ['-b:v', a.vbitrate]
    plog = os.path.join(a.chunks, 'x264pass')
    p1 = ['ffmpeg', '-v', 'error', '-y', '-i', video_only, '-map', '0:v:0', '-c:v', 'libx264', '-preset', 'slow', '-b:v', a.vbitrate, '-pix_fmt', 'yuv420p',
          '-profile:v', 'high', '-level', '4.1', '-r', '30', '-x264-params', 'keyint=60:min-keyint=30', '-pass', '1', '-passlogfile', plog, '-an', '-f', 'null', os.devnull]
    subprocess.run(p1, check=True)
    j = cmd.index('-c:a'); cmd[j:j] = ['-pass', '2', '-passlogfile', plog]
subprocess.run(cmd, check=True)
print('written', a.out, os.path.getsize(a.out)/1e6, 'MB')
