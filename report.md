# Raport: teledysk „Puste zasięgi” (Paweł Kuraś)

> Szkic – sekcje z wynikami weryfikacji są uzupełniane po każdym renderze (patrz „Historia wersji”).

## 1. Co powstało

| Plik / folder | Zawartość |
|---|---|
| `final/music-video.mp4` | teledysk 1920×1080, 30 kl./s, H.264 yuv420p, AAC; autor w metadanych i napisach: Paweł Kuraś |
| `scenariusz.md` | obsada (oryginalne lalki) i scenariusz z czasami |
| `linkedin_clone/` | samodzielny klon feedu (HTML/CSS/JS, własne ikony SVG); po otwarciu `index.html` w poście Henia odtwarza się `final/music-video.mp4` |
| `analysis/` | wyniki analizy muzyki (tekst, bity, części, dopasowanie słów) + wykresy kontrolne |
| `src/` | cały kod: analiza (`a01…a12`, `lyrics.py`, `g2p_pl.py`, `ps_align.py`), renderer (`src/video/`), render równoległy, montaż, weryfikacja |
| `checks/` | arkusze klatek, stopklatki, wyniki weryfikacji (`verify_file.json`, `verify_sync.json`) |
| `fonts/` | czcionki OFL użyte w obrazie i w klonie + pełny tekst licencji |
| `archive/` | poprzednie wersje (nic nie jest kasowane) |

Wymagane narzędzia (wszystkie darmowe, z menedżerów pakietów): `ffmpeg`, Python (`numpy`, `scipy`, `librosa`, `soundfile`, `skia-python`, `pocketsphinx`, `matplotlib`), `espeak-ng` + `mbrola-pl1` (apt), Node + Playwright/Chromium (preinstalowane). Żadnych gotowych nagrań ani grafik z internetu – cały obraz jest generowany kodem.
