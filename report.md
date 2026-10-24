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

## 2. Analiza muzyki (zanim cokolwiek zaprojektowałem)

### 2.1 Tekst → części i wersy
`tekst.rtf` (RTF, cp1250) zdekodowany do `analysis/lyrics.txt`, rozpisany przez `src/lyrics.py` na części, wersy, słowa i sylaby
(`analysis/lyrics_struct.json`): Intro (mowa) · Zwrotka 1 (4 wersy + mowa „Tak, tak…”) · Zwrotka 1 cd. (4) · Przedrefren (4) ·
Refren (6, z „(hej)” chóru) · Zwrotka 2 (mowa „Czekaj…” + 4) · wtrącenie chóru „(Wywalili na bruk!)” · Zwrotka 2 cd. (4) · Przedrefren (4) ·
Refren (6) · Bridge (mowa + 4) · Refren (6) · Outro (mowa + „Puste zasięgi! (hej!)”). Razem 53 wersy, 515 sylab wokalu prowadzącego.
Sylaby: jądro = samogłoska, „i” przed samogłoską jako zmiękczenie, przyimki bez samogłoski (w, z) doklejane do następnego słowa;
wymowa słów obcych zapisana ręcznie (LinkedInie, case study, cringe, scrollowania).

### 2.2 Siatka bitów, stopa / werbel / hi-hat (`src/a02_drums.py`, `analysis/beats.json`, wykresy `analysis/plots/02_*`)
* Onsety ze stemu perkusji: wspólna detekcja (strumień widmowy, krok 5 ms), klasyfikacja po przyroście energii w pasmach
  30–110 Hz (stopa), 1,5–5 kHz + 160–300 Hz (werbel), 7–18 kHz (hi-hat): **158 stóp, 103 werble, 84 hi-haty**.
* Okres i przesunięcie dopasowane do stopy (statystyka kołowa + MNK): **T = 0,40689 s (147,46 BPM), przesunięcie 0,2463 s**.
  Jedna stała siatka trafiała tylko 38% stóp w ±35 ms – resztki dryfowały do ±100 ms (tempo utworu pływa), więc siatka ma
  **lokalną korektę fazy** (ważona regresja reszt stopy i werbla w oknie ±2,6 s, rozwijanie fazy, zmiana ≤ 8 ms/bit).
  Wynik: **88% stóp w ±35 ms, mediana błędu 4,5 ms**; lokalny okres 0,399–0,415 s (144,6–150,4 BPM).
* „Raz” taktu: fazy 1 i 3 remisowały po perkusji (187 vs 185), rozstrzygnęły zmiany akordów (chroma basu/klawiszy: +9,4 vs −9,4)
  i ataki basu (+15,5) → faza 1. 521 bitów, 130 taktów.
* Siła akcentu na każdym bicie: szczyt obwiedni perkusji+perkusjonaliów w oknie bitu, znormalizowany 0–1 (pole `accent`).

### 2.3 Części z powtarzalności (`a03_sections.py`, `a03b_repeats.py`, `a06_melody_repeats.py`, `a12_structure.py`)
* Macierz samopodobieństwa taktów (progresja akordów instrumentów + chroma wokalu + MFCC), wzmocnienie po przekątnej, krzywa nowości.
  Najsilniejsze powtórzenia: blok **zwrotka 1b → przedrefren 1 → refren 1 powtórzony jako zwrotka 2b → przedrefren 2 → refren 2**
  z przesunięciem 41–42 takty (z = 2,27 i 2,17); refren 3 ~ takty 101–116.
* Niezależnie: chroma wokalu przesuwana po całym utworze – przedrefren 1 (46,3 s) pasuje do 112,9 s (0,90), refren 1 do 127,4 s (0,90–0,92).
* Granice części (`analysis/structure.json`) = początki wersów z dopasowania, dociągnięte do „raz” taktu przed pierwszym dźwiękiem.

### 2.4 Dopasowanie tekstu do nagrania słowo po słowie (forced alignment)
Modele ASR z HuggingFace/PyTorch nie dały się pobrać (proxy 403), więc użyłem lżejszych narzędzi offline:
1. **Zdarzenia sylabowe** ze stemu wokalu (`a08_syllable_events.py`): szczyty energii pasma formantów z narastaniem przed nimi
   (603 zdarzenia). Liczba zdarzeń we frazach zgadza się z liczbą sylab (np. 33,1–49,0 s: 58 zdarzeń = 49 sylab zwrotki 1b + 9 sylab
   pierwszego wersu przedrefrenu) – to ustaliło jednoznacznie przypisanie wersów do fraz.
2. **Programowanie dynamiczne** sylaby tekstu ↔ zdarzenia (`a09_align_dp.py`): koszt pominięcia zdarzenia, scalenia sylab,
   ciszy wewnątrz słowa, nienaturalnych odstępów; kotwice = początki fraz po pauzach; miękka siatka „wers co 2 takty”
   (zmierzona na pewnych wersach: refren 1 takty 36/38/40/42, refren 3 – 102/104/106/108).
3. **Priory fonetyczne z pocketsphinx** (model en-us z paczki pip + własny słownik polski→ARPAbet `g2p_pl.py`), tylko tam, gdzie
   dopasowanie się udało (19 wersów pojedynczo + odcinki) – 146 słów.
4. Wynik (`analysis/alignment.json`, kontrola `analysis/alignment_check.txt`): **497/516 sylab przypięte do zdarzenia wokalu**,
   19 interpolowanych; **99,7% początków słów wypada tam, gdzie wokal gra** (poziom w [t, t+150 ms] > −20 dB; jedyny wyjątek „tu” 134,39 s).
   Niezależne porównanie DP bez priorów z pocketsphinx: mediana 220 ms (46% < 200 ms) – metody się różnią, więc nie twierdzę,
   że granice słów są dokładne do kilkudziesięciu ms; po fuzji mediana różnicy 65 ms.
5. Finał chóralny (194–212 s) nie wynika jednoznacznie z tekstu – rozpisany ze spektrogramu (`analysis/plots/04_syl_finale.png`):
   rozciągnięte „Pu-ste za-się-gi” 194,7–201,4 s, okrzyk 201,5 s, szybka powtórka 208,2–209,3 s i „HEJ!” 209,78 s.

### 2.5 Ruch ust
* Wokal prowadzący = Henio: każda sylaba z dopasowania = jedno otwarcie szczęki (kształt: szybkie otwarcie, utrzymanie modulowane
  obwiednią wokalu, zamknięcie przed następną sylabą), szerokość wg samogłoski (a/o szeroko, i/u wąsko).
  Liczone **na siatce klatek**: każda sylaba ma ≥ 1 klatkę wyraźnego otwarcia, między sylabami ≥ 1 klatkę zamknięcia
  (przy szybkim śpiewie ~13 sylab/s to jedyny sposób, by przy 30 kl./s zachować „jedno otwarcie = jedna sylaba”).
* Chórki (stem „Backing Vocals”, 250 zdarzeń sylabowych) = Chór Zasięgów; „hej” i „Wywalili na bruk!” – chór.

## 3. Obsada i scenariusz
Pełny opis: `scenariusz.md`. Pomysł wynika z tekstu: piosenka mówi o wielkich gestach na LinkedInie, więc **cały teledysk jest filmem
w poście na (odtworzonym) LinkedInie**, a lalkowe show to treść tego posta. Przebitki do feedu wracają tam, gdzie tekst mówi o samym
serwisie: „Tak, tak, wszyscy się strasznie cieszą” (rosną reakcje, sypią się „Gratulacje!”), „Czekaj, ten wpis jest najlepszy” (przewinięcie
do wpisu Grażyny i wjazd w jej zdjęcie), refren 2 „wielkie zasięgi” (licznik wyświetleń do 1 254 302) i „A pod spodem cisza” (pusta sekcja
komentarzy), po bridge'u prosty wpis „Robię swoje.”, outro „miłego scrollowania” (przewijanie feedu) i statystyki na koniec.
Obsada (oryginalne lalki): Henio Kawka (narrator, cały wokal prowadzący), Grażyna Gratka, Prezes Bogumił Łaskawiec, Tadek Nowadroga,
Mirek Szacun, Kasia Kejs, Chór Zasięgów (8 lalek: 4 panów w przedrefrenach, panie dochodzą w refrenach – liczebność tylko rośnie).
Taniec nie jest głównym językiem: gesty ilustrują słowa (łyk kawy na „kawa”, ręka na żuchwie na „szczęka”, wyuczony uśmiech
i salut do czoła na „uśmiech wyuczony, rzut na czoło”, stempel „RESTRUKTURYZACJA” na „bruk”, aureola na „świętym”…), a rytmiczne
podrygi pojawiają się w refrenach (reakcje na patykach w górę na „raz” taktu, dociągnięte do prawdziwej stopy).

## 4. Realizacja obrazu
* **Renderer 2D (skia-python), bezstanowy**: każda klatka liczona wyłącznie z czasu t = n/30 (`src/video/render.py`). Ruch między pozami
  kluczowymi = splajn Hermite'a (pozy trzymane, przejścia 0,4–0,8 s, bez zatrzymań – stale działa „oddychanie”, bujanie w siatce bitów
  i wtórny ruch prętów); skoki pozycji tylko na cięciach (klucze < 50 ms traktowane jak skok, bez przestrzałów splajnu).
* **Lalki** (`puppet.py`, `cast.py`): głowa jako superelipsa przecięta linią ust dokładnie w kącikach; szczęka opada najmocniej pośrodku
  (zawias w kącikach), widać wnętrze ust i język; oczy-piłeczki z odblaskiem i filcowymi powiekami (mruganie deterministyczne), nos
  z pianki, futro z kosmyków (nagrane raz jako skia.Picture), faktura filcu (proceduralny szum włókien), dłonie-rękawiczki na prętach,
  ciało od pasa w górę zza krawędzi sceny, wejścia „z dołu” zza playboardu lub z boku (głowa obraca się w stronę ruchu).
* **Akcenty na prawdziwych uderzeniach**: kiwnięcie głową i przysiad lalki to impulsy w chwilach onsetów stopy/werbla ze stemu,
  błyski flesza i światła na werblu i „hej”; bujanie w fazie lokalnej siatki bitów.
* **Scena i studio** (`stage.py`): portal z żarówkami (pogoń w rytm), kurtyna z aksamitu, krawędź sceny, dekoracje z tektury dla każdej
  części (kuchnia, biuro, ścianka konferencyjna, wielka scena show z podestem chóru, studio Grażyny, droga z bruku, korporacyjny raj,
  studio w drewnie, „pod spodem” – zaplecze lalkarzy), reflektory, snopy w zadymieniu, cienie lalek na dekoracji.
* **Kamery** (`timeline.py`): perspektywa warstw (tło, dekoracje, chór, lalki, krawędź sceny, kurtyna, portal na różnych głębokościach),
  więc tło ma stałe miejsce w świecie i poprawną paralaksę; 62 ujęcia, w każdym ruch (najazd/odjazd/panorama/żuraw), cięcia na
  początkach wersów lub na „raz” taktu; trzy refreny mają różne zestawy ujęć (ogólny z żurawiem + zejście „pod spodem”; żuraw z góry +
  przebitki do analityki i pustych komentarzy; plan z daleka całego studia + przejazd + cisza we dwóch).
* **Napisy jako scenografia** (`signs.py`): tablice z tektury na sznurkach, neon na tablicy portalu, malowane litery na froncie krawędzi
  sceny, dymki do kwestii mówionych, karton pisany markerem (bridge), kreda na sklejce (pod spodem), pole komentarza / czat w feedzie.
  Każdy wers ma jedno stałe miejsce w świecie; miejsce wybierane automatycznie spośród kandydatów tak, by napis był w kadrze i nie
  nachodził na żadną postać w całym czasie trwania wersu; słowa pojawiają się w chwili zaśpiewania (czasy z dopasowania).
* **Klon LinkedIna** (`linkedin_clone/`): HTML/CSS/JS od zera (Inter OFL, własne ikony SVG, awatary = portrety lalek z renderera).
  Stany strony (komentarze, czat, analityka, prosty wpis) przechwytywane Playwrightem (`src/video/capture_clone.js`), a w teledysku
  (`linkedin.py`) składane z: przewijaniem, „kamerą” na ekranie przeglądarki, filmem ze sceny na żywo w ramce posta (wjazd w kadr filmu
  kończy się dokładnie na pierwszej klatce następnego ujęcia), licznikami rosnącymi klatka po klatce i pisaniem słowo po słowie.
* **„Ludzki” wygląd** (`post.py`): halacja (jasne partie rozmyte i dodane ciepłym tonem), lekka miękkość, ziarno (12 klatek szumu
  wybieranych i przesuwanych deterministycznie od numeru klatki), winieta; w przebitkach obróbka słabsza i narasta przy wjeździe w film.
* **Render** (`src/render_all.py`, `src/assemble.py`): kawałki po 300 klatek, 4 procesy równolegle, każdy kawałek kodowany x264 CRF 14,
  sklejenie bez rekompresji, końcowe kodowanie H.264 yuv420p + AAC z całego MP3 (bez filtrów i cięć). Każda wersja renderowana
  z zamrożonej kopii kodu (`build/vN/src`).
