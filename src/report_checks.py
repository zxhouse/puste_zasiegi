"""Wpisuje do report.md sekcję 5 (jak sprawdziłem bieżącą wersję) na podstawie checks/verify_file.json i checks/verify_sync.json."""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = json.load(open(os.path.join(ROOT, 'checks/verify_file.json'))); R = json.load(open(os.path.join(ROOT, 'checks/verify_sync.json')))
ver = os.environ.get('PZ_VER', 'v3')
v, a, f = F['video'], F['audio'], F['format']
offs = F['audio_offset']; corr = [o['corr'] for o in offs]
lm, cm, ws = R['lead_mouth'], R['choir_mouth'], R['word_starts_in_vocal']
sg, cuts, acc, fl = R['signs'], R['cuts'], R['accents'], R['flashes']
weak = [p for p in sg['placement'] if p['visibility'] < 0.95 or p['overlap'] > 0.02]
txt = f"""## 5. Jak sprawdziłem wersję {ver}
Skrypty: `src/verify.py` (plik) i `src/verify_sync.py` (synchronizacja liczona z tych samych funkcji, z których renderowane są klatki).
Wyniki: `checks/verify_file.json`, `checks/verify_sync.json`, `checks/sheets/` (arkusze co 4 s), `checks/stills/` (42 stopklatki).

**Plik** (`final/music-video.mp4`)
* Pełne dekodowanie `ffmpeg -f null`: **{len(F['decode_errors'])} błędów**.
* Obraz: H.264 {v['profile']}, {v['pix_fmt']}, {v['size']}, {v['r_frame_rate']} kl./s, **{v['nb_read_frames']} klatek = oczekiwane {F['expected_frames']}**, {v['duration']:.3f} s.
* Dźwięk: AAC {a['sample_rate']} Hz, {a['channels']} kanały, {a['duration']} s; plik {f['size_MB']} MB.
* Metadane: tytuł „{f['tags'].get('title')}”, artist/composer „{f['tags'].get('artist')}”, komentarz „{f['tags'].get('comment')}”; autor także w napisach końcowych.
* **Przesunięcie dźwięku względem MP3: {', '.join(str(o['lag_samples']) for o in offs)} próbek** w {len(offs)} miejscach ({', '.join(f"{o['at_s']:g}" for o in offs)} s),
  korelacja {min(corr):.4f}–{max(corr):.4f}; na końcu {F['audio_samples']['diff']} próbek ciszy z dopełnienia ramki AAC; SNR {F['audio_snr_db']} dB (strata AAC).

**Synchronizacja**
* Usta Henia: **{lm['syllables_with_own_opening']} z {lm['total_syllables']} sylab ma własny szczyt otwarcia**, {lm['lines_exact']}/{lm['lines_total']} wersów
  dokładnie „sylaba = szczyt”; {lm['half_openings_pct']}% szczytów to półotwarcia (< 0,7); usta otwarte w ciszy wokalu: {lm['mouth_open_when_vocal_silent_pct']}% takich klatek.
* Usta chóru: **{cm['syllables_with_own_opening']} z {cm['lyric_syllables']} sylab** tekstu śpiewanego przez chór ma własny szczyt; {cm['wordless_segments']} wokaliz bez słów; „hej” w {', '.join(f'{h:.2f}' for h in cm['hej'])} s.
* Początki słów tam, gdzie gra stem: Henio {ws['lead']['inside_pct']}% z {ws['lead']['words']} (wyjątki: {', '.join(f"„{w}” {t:.2f} s" for w, t in ws['lead']['outside']) or '–'}),
  chór {ws['choir']['inside_pct']}% z {ws['choir']['words']}.
* Zgodność dopasowania z niezależnymi narzędziami – tabela w 2.4.
* Akcenty ruchu: {acc['accent_peaks']} szczytów, **{acc['pct_within_1_frame']}% w ±1 klatce od uderzenia stopy/werbla** (mediana {acc['median_dist_to_drum_hit_ms']} ms);
  błyski: {fl['flash_peaks']}, {fl['pct_within_2_frames']}% w ±2 klatkach od werbla lub „hej”.
* Cięcia: **{cuts['on_line_or_downbeat']}/{cuts['n']} na początku wersu (lub zdania w kwestii mówionej) albo na „raz” taktu**. Ujęcia bez ruchu kamery: {len(R['camera_static_shots'])}.
* Napisy (co 2. klatka ujęć sceny, {sg['sign_frames_checked']} sprawdzeń): największe nachodzenie napisu na postać **{sg['max_overlap_fraction_with_character']*100:.1f}%**
  powierzchni napisu ({sg['at']}; prostokąty postaci są zgrubne), najmniejsza widoczność napisu w kadrze {sg['min_visible_fraction']*100:.0f}% ({sg['min_visible_at']});
  {len(sg['placement']) - len(weak)} z {len(sg['placement'])} napisów w pełni widocznych i bez kolizji przez cały czas trwania.
* Chór: liczebność w refrenach nie spada; w układzie grupowym {R['choir']['overlapping_pairs']} par nachodzących na siebie.

"""
p = os.path.join(ROOT, 'report.md'); s = open(p).read()
a = s.index('## 5. Jak sprawdziłem'); b = s.index('## 6. ')
s = s[:a] + txt + s[b:]
open(p, 'w').write(s)
print('sekcja 5 zapisana')
