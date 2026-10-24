"""Napisy końcowe (v5): długie, przewijane - autorstwo, narzędzia i co robiły, fonty. Jawnie: co jest twórczością autora,
co zrobił model AI (Suno V6 - aranż; Claude Opus 5.5 - realizacja obrazu w kodzie) i w jakim trybie."""
import skia, math, functools
import engine as E
from engine import smoothstep
from gfx import draw_text, light_pool, font, text_width

GOLD, CREAM, MUTED, ROSE = '#f6d47a', '#efe6da', '#a89c8f', '#e9a6c2'
# (rodzaj, tekst) - 'title' tytuł, 'h' nagłówek sekcji, 'role' (rola, kto), 'tool' (narzędzie, co robiło), 'p' akapit, 'gap' odstęp
ITEMS = [
    ('title', 'Puste zasięgi'), ('gap', 30),
    ('h', 'MUZYKA'),
    ('role', ('Kompozycja i muzyka', 'Paweł Kuraś')),
    ('role', ('Tekst', 'Paweł Kuraś')),
    ('role', ('Wstępna wersja utworu', 'Paweł Kuraś')),
    ('role', ('Ostateczna aranżacja chóralno-wokalna', 'Suno V6 (model AI)')),
    ('p', 'na podstawie kompozycji, tekstu i wstępnej wersji Pawła Kurasia'), ('gap', 60),
    ('h', 'TELEDYSK'),
    ('role', ('Pomysł, kierownictwo artystyczne', 'Paweł Kuraś')),
    ('role', ('Decyzje i uwagi do każdej wersji', 'Paweł Kuraś')),
    ('role', ('Scenariusz, lalki, scenografia, animacja', 'Claude Opus 5.5 (Anthropic)')),
    ('role', ('Kamera, montaż, klon serwisu, weryfikacja', 'Claude Opus 5.5 (Anthropic)')),
    ('p', 'Claude Opus 5.5 pracował w Claude Code: sesja w chmurze (zdalny kontener),'),
    ('p', 'tryb automatyczny (samodzielne uruchamianie poleceń i programów), rozszerzone rozumowanie;'),
    ('p', 'cały obraz powstał z kodu, bez gotowych grafik i nagrań; 6 wersji, każda poprawiana według uwag autora'), ('gap', 60),
    ('h', 'NARZĘDZIA I CO ROBIŁY'),
    ('tool', ('Omnilingual ASR CTC 1B (Meta) · onnxruntime', 'rozpoznanie i dopasowanie tekstu do wokalu, słowo po słowie')),
    ('tool', ('Montreal Forced Aligner · polish_mfa', 'granice głosek i sylab - jedno otwarcie ust na sylabę')),
    ('tool', ('NVIDIA Parakeet TDT 0.6B v3 · sherpa-onnx', 'niezależna kontrola czasów słów')),
    ('tool', ('Whisper small · faster-whisper', 'niezależna kontrola czasów słów')),
    ('tool', ('Silero VAD', 'kontrola, czy słowa leżą tam, gdzie jest głos')),
    ('tool', ('librosa · NumPy · SciPy · soundfile', 'bity, stopa i werbel, części utworu, obwiednia głosu (trzymane nuty)')),
    ('tool', ('pocketsphinx · espeak-ng · MBROLA', 'pierwsze dopasowanie tekstu (wersje 1-2)')),
    ('tool', ('skia-python', 'lalki, scenografia, światło, cienie, napisy - każda klatka liczona z czasu')),
    ('tool', ('HTML · CSS · JavaScript', 'klon serwisu zbudowany od zera')),
    ('tool', ('Playwright · Chromium', 'zrzuty klonu serwisu do przebitek')),
    ('tool', ('FFmpeg · x264 · AAC', 'kodowanie obrazu i dźwięku (dźwięk z oryginalnego pliku, bez zmian)')),
    ('tool', ('matplotlib', 'wykresy kontrolne analizy')),
    ('tool', ('Python · Node.js', 'cały kod: analiza, renderer, montaż, testy')), ('gap', 60),
    ('h', 'FONTY (SIL OPEN FONT LICENSE)'),
    ('p', 'Titan One · Cherry Bomb One · Rammetto One · Sigmar One · Shrikhand'),
    ('p', 'Kalam · Caveat Brush · Bajaderka · Montserrat · Inter'), ('gap', 70),
    ('p', 'Lalki, postaci, wpisy i serwis w kadrze są fikcyjne.'),
    ('p', 'Klon interfejsu wykonany od zera na potrzeby teledysku.'), ('gap', 90),
    ('end', 'Puste zasięgi'), ('endsub', 'Paweł Kuraś · 2026'),
]
LH = {'title': 170, 'h': 92, 'role': 66, 'tool': 92, 'p': 46, 'end': 150, 'endsub': 70}
SPEED = 184.0                      # px/s przewijania (v6: 2x szybciej)
LEAD_IN = 0.6                      # napisy wjeżdżają od razu na zasuniętą kurtynę
@functools.lru_cache(None)
def layout():
    y = 0.0; out = []
    for kind, v in ITEMS:
        if kind == 'gap': y += v; continue
        out.append((y, kind, v)); y += LH[kind]
    return out, y
def duration():
    """Długość napisów: wjazd od dołu, przewinięcie całości, ostatnia plansza zatrzymuje się na środku na 3 s."""
    items, total = layout()
    y_end = [y for y, k, v in items if k == 'end'][0]
    return LEAD_IN + (E.H + y_end - E.H/2 + 40)/SPEED + 3.0
_CAM = []
def render_credits(cv, t, sc):
    """v6: tło napisów = scena z zasuniętą kurtyną (ciągłość z ostatnim ujęciem), przygaszona; pod koniec wyciemnienie do czerni."""
    import timeline as T, compose as CP
    if not _CAM: _CAM.append(T.cam_at(E.SONG_DUR - 0.01))
    u = t - E.SONG_DUR
    CP.render_stage(cv, T.stage_scene(t, _CAM[0], signs=False), t)
    dim = 0.35 + 0.42*smoothstep(u/1.2) + 0.23*smoothstep((u - (E.TAIL - 1.6))/1.4)
    cv.drawRect(skia.Rect(0, 0, E.W, E.H), skia.Paint(Color4f=skia.Color4f(0.02, 0.01, 0.03, min(dim, 1.0))))
    a = smoothstep(u/0.5)*(1 - smoothstep((u - (E.TAIL - 1.0))/0.9))
    if a <= 0.001: return
    items, total = layout()
    y_end = [y for y, k, v in items if k == 'end'][0]
    off = E.H - max(u - LEAD_IN, 0.0)*SPEED                    # pozycja góry listy na ekranie
    off = max(off, E.H/2 - 40 - y_end)                         # ostatnia plansza staje na środku
    cx = E.W/2
    for y, kind, v in items:
        yy = off + y
        if yy < -200 or yy > E.H + 200: continue
        edge = min(smoothstep((yy + 60)/160), smoothstep((E.H + 60 - yy)/160))      # miękkie wejście/wyjście przy krawędziach
        al = a*edge
        if al <= 0.01: continue
        if kind == 'title': draw_text(cv, v, cx, yy + 110, 'script', 120, GOLD, alpha=al)
        elif kind == 'end': draw_text(cv, v, cx, yy + 100, 'script', 110, GOLD, alpha=al)
        elif kind == 'endsub': draw_text(cv, v, cx, yy + 44, 'credits2', 38, CREAM, alpha=al)
        elif kind == 'h': draw_text(cv, v, cx, yy + 52, 'credits', 34, ROSE, alpha=al)
        elif kind == 'role':
            draw_text(cv, v[0], cx - 30, yy + 40, 'credits2', 34, MUTED, 'right', alpha=al, maxw=820)
            draw_text(cv, v[1], cx + 30, yy + 40, 'credits', 34, CREAM, 'left', alpha=al, maxw=820)
        elif kind == 'tool':
            draw_text(cv, v[0], cx, yy + 34, 'credits', 32, CREAM, alpha=al, maxw=1600)
            draw_text(cv, v[1], cx, yy + 72, 'credits2', 27, MUTED, alpha=al, maxw=1600)
        elif kind == 'p': draw_text(cv, v, cx, yy + 32, 'credits2', 29, CREAM, alpha=al*0.92, maxw=1700)
