# Raport: teledysk „Puste zasięgi” (Paweł Kuraś)

> Stan: **wersja v2** (`final/music-video.mp4`). Poprzednia wersja: `archive/v1/`. Wyniki sprawdzeń poniżej dotyczą v2.
> Nie słuchałem ani nie oglądałem filmu – wszystko niżej to pomiary liczbowe i obejrzane pojedyncze klatki / arkusze klatek.

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
  wybieranych i przesuwanych deterministycznie od numeru klatki, zmiana co 2 klatki), winieta; w przebitkach obróbka słabsza i narasta przy wjeździe w film.
* **Render** (`src/render_all.py`, `src/assemble.py`): kawałki po 300 klatek, 4 procesy równolegle, każdy kawałek kodowany x264 CRF 14,
  sklejenie bez rekompresji, końcowe kodowanie H.264 yuv420p (dwa przebiegi, 3200 kb/s – żeby plik zmieścił się w limicie
  100 MB na pojedynczy plik w GitHubie) + AAC 320 kb/s z całego MP3 (bez filtrów i cięć). Każda wersja renderowana z zamrożonej
  kopii kodu (`build/vN/src`).

## 5. Jak sprawdziłem wersję v2
Skrypty: `src/verify.py` (plik) i `src/verify_sync.py` (synchronizacja liczona z tych samych funkcji, z których renderowane są klatki).
Wyniki: `checks/verify_file.json`, `checks/verify_sync.json`, `checks/sheets/` (arkusze co 4 s), `checks/stills/` (42 stopklatki z kluczowych momentów).

**Plik** (`final/music-video.mp4`)
* Pełne dekodowanie `ffmpeg -f null`: **0 błędów**.
* Obraz: H.264 High, yuv420p, 1920×1080, 30/1 kl./s, **6482 klatki = oczekiwane 6482** (212,04 s piosenki + 4 s wyciemnienia i napisów), 216,067 s.
* Dźwięk: AAC 48 kHz stereo, ~314 kb/s, 212,0 s; plik 94,87 MB (limit GitHuba na plik to 100 MB).
* Metadane: tytuł „Puste zasięgi”, artist / author / composer „Paweł Kuraś”, komentarz „Teledysk: Paweł Kuraś”; ten sam autor w napisach końcowych.
* **Przesunięcie dźwięku względem oryginalnego MP3: 0 próbek** w 8 miejscach (5, 30, 61, 100, 140, 170, 200, 210 s), korelacja 0,9996–0,9999.
  Długość: MP4 ma 10 176 512 próbek, MP3 10 176 000 – na końcu jest 512 próbek ciszy z dopełnienia ramki AAC (początek się zgadza).
  Stosunek sygnał/różnica 36,1 dB – to strata kodowania AAC, nie zmiana treści (bez filtrów, cięć i zmiany głośności).

**Synchronizacja**
* Usta Henia: **515 sylab wokalu → 515 otwarć szczęki**, każda sylaba ma własne otwarcie, 52/52 wersów dokładnie „sylaba = otwarcie”.
  Usta otwarte w klatkach, w których wokal milczy: 3,6% takich klatek (końcówki zamykania i ~12 ms wyprzedzenia przed sylabą).
  Korelacja otwarcia z obwiednią wokalu 0,57 – umiarkowana, bo usta celowo zamykają się między sylabami, a obwiednia nie spada do zera.
* Chór: 263 otwarcia na 250 zdarzeń sylabowych stemu chórków, mediana odległości 37 ms, 92,8% w ±100 ms;
  wtrącenie „(Wywalili na bruk!)”: **6 sylab → 6 otwarć**.
* Akcenty ruchu (kiwnięcia, przysiady): 183 szczyty, **100% w ±1 klatce od prawdziwego uderzenia stopy/werbla** (mediana 8,8 ms).
  Błyski świateł: 13, wszystkie w ±2 klatkach od werbla lub „hej” (mediana 13 ms).
* Cięcia: **59/59 na początku wersu (lub zdania w kwestii mówionej) albo na „raz” taktu** (±70 ms). Ujęć bez ruchu kamery: 0.
* Napisy: w 1893 sprawdzonych klatkach-napisach (co 2. klatka ujęć sceny) **największe nachodzenie napisu na postać: 0%**
  (w kodzie sprzed poprawki opisanej w 7.2.3: 21% w 148,1 s).
* Chór: w żadnym refrenie liczba lalek nie spada, tylko rośnie (do 8); w układzie grupowym 0 par nachodzących na siebie.

**Obejrzane klatki**: oba arkusze (co 4 s, cały film) i stopklatki; dodatkowo pojedyncze klatki z gotowego pliku w 71,0 s („pod spodem”),
100,8 s („Wywalili” na krawędzi sceny), 152,0 s i 155,5 s (bridge: napisy wersów na tekturze obok kartonu „Robię swoje.”).

## 6. Niepewności i rzeczy do decyzji
* **Granice słów**: dopasowanie bez modelu ASR dla polskiego. Liczba sylab i otwarć ust zgadza się co do jednej, ale czasy pojedynczych
  sylab mogą odbiegać o kilkadziesiąt ms (dwie niezależne metody różniły się medianą 220 ms przed fuzją, 65 ms po niej; 19 z 516 sylab
  interpolowanych). Najmniej pewne: szybkie fragmenty zwrotki 2 i finał chóralny (194–212 s), rozpisany ręcznie ze spektrogramu.
* **Chórki**: otwarcia chóru idą za zdarzeniami wykrytymi w stemie chórków (263 otwarcia na 250 zdarzeń – kilka długich nut
  rozbitych na dwa otwarcia); poza wtrąceniem „Wywalili na bruk!” nie mam dla chórków tekstu sylaba po sylabie.
* **Kompresja**: wersja v2 jest kodowana do stałej przepływności 3200 kb/s, żeby zmieścić się w 100 MB na GitHubie. W scenach z ziarnem
  i konfetti może to dać lekką „kaszę”; kawałki pośrednie (CRF 14, `build/v2/chunks`) są lepszej jakości i można z nich zrobić plik bez
  limitu rozmiaru (`python3 src/assemble.py build/v2/chunks <plik> --crf 16`).
* **Klon LinkedIna**: zgodnie z prośbą odtwarza wygląd serwisu 1:1 (układ, kolory, nazwa w tekście piosenki i na stronie). W stopce klonu
  jest linijka „LinkedIn Corporation © 2026” jak w oryginale, obok dopisek, że to klon zrobiony na potrzeby teledysku, a w napisach
  końcowych – „Lalki, scenografia i serwis w kadrze są fikcyjne”. Przed publikacją warto zdecydować, czy zostawić nazwę i stopkę.
* **Interpretacje**: finał (wszyscy wracają na scenę, „Puste zasięgi! HEJ!” na neonie) i scena „pod spodem” (widok od strony lalkarzy)
  to moje odczytanie tekstu, nie coś, co wynika z niego jednoznacznie.

## 7. Historia wersji

### 7.1 v1
Pierwsza pełna wersja: 6482 klatki, 94,82 MB, kodowanie CRF. Plik i wynik sprawdzenia pliku: `archive/v1/` (opis w `archive/v1/NOTES.md`).
Przejrzałem jej arkusze i stopklatki i na tej podstawie zrobiłem poprawki v2 poniżej.

### 7.2 v2 – poprawki

#### 7.2.1 Pusty napis wtrącenia chóru „(Wywalili na bruk!)”
* Problem: w v1 w 99,6–102,9 s na krawędzi sceny była pusta, wąska tablica. Przyczyna: funkcja tekstu napisu wycinała wszystko w nawiasach
  (żeby ukryć chórowe „(hej)” w wersach Henia), a ten wers jest cały w nawiasie.
* Poprawka (`signs.py`): jeśli po wycięciu nawiasów nic nie zostaje, napis pokazuje tekst z nawiasu.
* Sprawdzenie: klatka 100,8 s z pliku v2 – „Wywalili”, klatka 102,2 s – „Wywalili na bruk!”.

#### 7.2.2 Usta chóru we wtrąceniu: 8 otwarć na 6 sylab
* Problem: usta chóru szły za surowymi zdarzeniami stemu chórków, a w tym wersie detektor znalazł ich więcej niż sylab.
* Poprawka (`engine.py`): dla wersów śpiewanych tylko przez chór otwarcia biorą się z sylab dopasowanego tekstu.
* Sprawdzenie: otwarcia w 99,93 / 100,27 / 100,80 / 101,00 / 101,67 / 101,90 s = Wy-wa-li-li-na-bruk (6/6).

#### 7.2.3 Napisy wjeżdżały jeszcze w poprzednim ujęciu
* Problem: tablica pojawiała się 0,4 s przed pierwszym słowem. Cięcia są na początkach wersów, więc w 46 z 48 napisów na scenie tablica / neon
  pojawiały się pod koniec poprzedniego ujęcia; w 148,1–148,85 s pusty dymek bridge'u zasłaniał głowę lalki z chóru (21% powierzchni napisu).
* Poprawka (`signs.py`, `timeline.py`): jeśli wers zaczyna się na cięciu (cięcie do 0,75 s przed pierwszym słowem), tablica po prostu
  wisi już w nowym ujęciu od pierwszej klatki – bez wjazdu w poprzednim.
* Sprawdzenie: klatki 14,10 / 14,20 / 148,6 / 148,9 s; w teście napisów nachodzenie spadło z 21% do 0%.

#### 7.2.4 Jedno otwarcie = jedna sylaba także przy szybkim śpiewie
* Problem: w v1 otwarcie ust liczone było w czasie ciągłym; przy ~13 sylabach/s dwie krótkie sylaby mogły wypaść w tej samej klatce
  albo bez klatki zamknięcia między nimi.
* Poprawka (`engine.py`): usta liczone na siatce klatek – każda sylaba ma ≥ 1 klatkę otwarcia, między sylabami ≥ 1 klatkę zamknięcia.
* Sprawdzenie: 515/515 sylab z własnym otwarciem, 52/52 wersów dokładnie.

#### 7.2.5 Scena „A pod spodem cisza”
* Problem: w v1 (klatka 71,5 s) widać było tylko czarne, nieczytelne sylwetki rąk na tle sklejki, bez lalek.
* Poprawka (`under.py`, kamera w `timeline.py`): widok zza krawędzi sceny – nad krawędzią plecy lalek w ciepłym świetle show,
  pod nią lalkarze w czerni z prętami, zimne światło robocze, wers kredą na sklejce.
* Sprawdzenie: klatka 71,0 s z pliku v2 i arkusz (1:08).

#### 7.2.6 Repryza: lalki wychylały się przed cięciem
* Problem: wejścia na repryzę zaczynały się 0,2–0,25 s przed jej początkiem, czyli jeszcze w poprzednim ujęciu.
* Poprawka (`timeline.py`): wejścia startują 0,35–0,4 s po „raz” taktu, od którego zaczyna się ujęcie repryzy.

#### 7.2.7 Drobne
* Napis „Puste zasięgi” na froncie sceny niżej i mniejszy (zasłaniał dłonie lalek w planach ogólnych).
* Wyciemnienie obrazu od 210,6 s przed napisami końcowymi.
* Ziarno zmienia się co 2 klatki i jest słabsze (0,12 zamiast 0,16) – spokojniejsze i lepiej znosi kompresję.
* Kodowanie dwuprzebiegowe 3200 kb/s – plik mieści się w limicie 100 MB na GitHubie.
