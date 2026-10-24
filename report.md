# Raport: teledysk „Puste zasięgi” (Paweł Kuraś)

> Stan: **wersja v3** (`final/music-video.mp4`). Poprzednie wersje: `archive/v1/`, `archive/v2/`. Wyniki sprawdzeń poniżej dotyczą v3.
> Nie słuchałem ani nie oglądałem filmu – wszystko niżej to pomiary liczbowe i obejrzane pojedyncze klatki / arkusze klatek.

## 1. Co powstało

| Plik / folder | Zawartość |
|---|---|
| `final/music-video.mp4` | teledysk 1920×1080, 30 kl./s, H.264 yuv420p, AAC; autor w metadanych i napisach: Paweł Kuraś |
| `scenariusz.md` | obsada (oryginalne lalki) i scenariusz z czasami |
| `linkedin_clone/` | samodzielny klon feedu (HTML/CSS/JS, własne ikony SVG); po otwarciu `index.html` w poście Henia odtwarza się `final/music-video.mp4` |
| `analysis/` | wyniki analizy muzyki (tekst, bity, części, dopasowanie słów) + wykresy kontrolne |
| `src/` | cały kod: analiza (`a01…a12`; v3: `a20…a25` – modele mowy, dopasowanie, fuzja), renderer (`src/video/`), render równoległy, montaż, weryfikacja |
| `checks/` | arkusze klatek, stopklatki, wyniki weryfikacji (`verify_file.json`, `verify_sync.json`) |
| `fonts/` | czcionki OFL użyte w obrazie i w klonie + pełny tekst licencji |
| `archive/` | poprzednie wersje filmu: `v1/`, `v2/` (nic nie jest kasowane) |
| `analysis/asr/` | surowe wyniki modeli mowy: transkrypcje Omnilingual (stem prowadzący i chórki), Whisper, Parakeet, Silero VAD, dopasowania CTC i MFA |

Wymagane narzędzia (wszystkie darmowe, z menedżerów pakietów): `ffmpeg`, Python (`numpy`, `scipy`, `librosa`, `soundfile`, `skia-python`, `pocketsphinx`, `matplotlib`, `onnxruntime`, `sherpa-onnx`, `faster-whisper`, `silero-vad`), Montreal Forced Aligner (conda-forge, przez micromamba), `espeak-ng` + `mbrola-pl1` (apt), Node + Playwright/Chromium (preinstalowane). Modele mowy (pobierane do `tools/models/`, poza repozytorium): Omnilingual ASR CTC 1B i Parakeet TDT v3 (wydania sherpa-onnx), `polish_mfa` (wydania mfa-models, CC BY 4.0), Whisper small CT2 (npm). Żadnych gotowych nagrań ani grafik z internetu – cały obraz jest generowany kodem.

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

### 2.4 Dopasowanie tekstu do nagrania słowo po słowie (v3: modele rozpoznawania mowy)
W v1/v2 modele ASR nie były dostępne (HuggingFace i serwery modeli są zablokowane w tym środowisku), a dopasowanie z detektora
sylab i programowania dynamicznego okazało się miejscami przesunięte o cały wers. W v3 pobrałem modele innymi, dozwolonymi drogami
(wydania na GitHubie, rejestr npm, conda-forge, PyPI) i użyłem kilku niezależnych narzędzi na **stemach wokalu** (prowadzący i chórki osobno):

| Narzędzie | Skąd | Do czego |
|---|---|---|
| **Omnilingual ASR CTC 1B** (Meta, int8 ONNX, 1600 języków) | wydanie `asr-models` projektu k2-fsa/sherpa-onnx | prawdopodobieństwa znaków co 20 ms → transkrypcja + wymuszone dopasowanie CTC (Viterbi) znanego tekstu |
| **Montreal Forced Aligner 3.4** + model `polish_mfa` 2.0.0a, słownik i g2p | conda-forge + wydania MontrealCorpusTools/mfa-models (CC BY 4.0) | czasy słów i **fonemów** (granice sylab) |
| **Whisper small** (CTranslate2 int8, faster-whisper) | rejestr npm (4 części, suma SHA-256 zgodna z deklarowaną) | niezależne rozpoznanie z czasami słów (kontrola) |
| **NVIDIA Parakeet TDT 0.6B v3** (int8 ONNX, języki europejskie) | wydanie `asr-models` sherpa-onnx | niezależne rozpoznanie z czasami tokenów (kontrola) |
| **Silero VAD** | PyPI | gdzie w stemie jest głos (kontrola) |

Kroki (`src/a20…a25`):
1. **Transkrypcja Omnilingual** stemu prowadzącego (`build/asr/omni_lead_greedy.txt`) – praktycznie bezbłędnie odtwarza tekst,
   z czasami. Już ona pokazała, gdzie stare dopasowanie się myliło (np. „Ktoś robi z życia case study” śpiewane od 100,4 s, a w v2
   ustawione na 102,9 s – cała zwrotka 2b przesunięta o jeden wers).
2. **Wymuszone dopasowanie CTC całego tekstu** z możliwością pominięcia słowa (kara zależna od długości słowa) – osobno na stemie
   prowadzącym i na stemie chórków (chórki w oknach czasowych części, żeby powtarzane frazy nie „przeskakiwały” między refrenami).
   Z tego wynika, **kto śpiewa które słowo** (Henio / chór / oba – patrz `scenariusz.md`, „Kto śpiewa co”).
3. **Weryfikacja wariantów tekstu** akustycznie: przymiotnik przed „zasięgi” (puste / wielkie / mocne) wybierany po wyniku
   dopasowania w oknie słowa. Jedna różnica: refren 1, wers 6 – śpiewane **„Puste zasięgi”** (wynik −0,07 wobec −1,22 dla „Wielkie”).
4. **MFA** na wersach (granice segmentów z kroku 2 ± 0,6 s, 14 słów spoza słownika przez g2p) – fonemy dla 504 z 521 sylab.
5. **Fuzja**: początek słowa = MFA, jeśli zgadza się z CTC (± 150 ms po poprawce o 45 ms – CTC „strzela” chwilę po początku
   dźwięku), inaczej CTC; sylaby z grup fonemów MFA wokół samogłosek (inaczej ze znaczników znaków CTC); koniec trzymanej nuty
   z obwiedni stemu (spadek o 18 dB). Słowa nierozpoznane pewnie („case”, „cringe”, „Że” w 55,9 s) – pozycja z pierwszego wymuszonego
   dopasowania. Wynik: `analysis/alignment.json` (poprzedni: `analysis/alignment_v2.json`).
6. **„Hej”**: w stemie chórków okrzyki są tylko w refrenie 3 (182,4 i 185,7 s, +34 i +56 dB); w refrenach 1–2 ich w nagraniu nie ma.
   Okrzyk Henia 201,5 s i końcowe „HEJ” 209,8 s – z obwiedni stemu prowadzącego. Wokalizy chóru bez słów (12 odcinków,
   szczyt > maks − 11 dB) – „uuu” chóru.

**Zgodność z niezależnymi narzędziami** (początki 243 słów wokalu prowadzącego, `analysis/alignment_crosscheck.json`, wykres
`analysis/plots/20_crosscheck.png`):

| Narzędzie | mediana różnicy | w ±100 ms | w ±200 ms | > 0,5 s |
|---|---|---|---|---|
| MFA | 50 ms | 89.3% | 97.9% | 3 |
| Parakeet TDT v3 | 60 ms | 72.9% | 91.9% | 0 |
| Whisper small | 80 ms | 61.2% | 85.7% | 6 |
| stare dopasowanie (v2) | 60 ms | 56.9% | 71.8% | 14 (+41 słów nieznalezionych w ±1,5 s) |

Silero VAD: 98.4% początków słów leży w odcinkach z głosem (wyjątki: 4 razy „Puste” na początku refrenu – śpiewany początek frazy).

### 2.5 Ruch ust
* Henio = stem prowadzący: **jedna sylaba = jeden ruch szczęki**, ale wielkość otwarcia zależy od sylaby: samogłoska (a szeroko,
  o/e średnio, u/i/y wąsko) × głośność stemu w sylabie × długość × akcent (przedostatnia sylaba mocniej, krótkie słowa
  funkcyjne słabiej) – stąd **półotwarcia** (0,22–1,0). Między sylabami szczęka przymyka się do „dołka” (≤ 32% mniejszego
  z sąsiednich otwarć), a całkowicie domyka przed m/b/p i w przerwach. Dla o/u usta się **zaokrąglają** (otwarcie skupione
  w środku). Długa nuta: otwarcie lekko przymyka się w trakcie trzymania.
* Liczone na siatce klatek: każda sylaba ma klatkę z ≥ 85% swojego otwarcia, między sylabami jest klatka z dołkiem.
* Chór = stem chórków: sylaby dopasowanego tekstu (tam, gdzie chór śpiewa słowa), „uuu” we wokalizach bez słów, „hej” tylko w refrenie 3.

## 3. Obsada i scenariusz
Pełny opis: `scenariusz.md`. Pomysł wynika z tekstu: piosenka mówi o wielkich gestach na LinkedInie, więc **cały teledysk jest filmem
w poście na (odtworzonym) LinkedInie**, a lalkowe show to treść tego posta. Przebitki do feedu wracają tam, gdzie tekst mówi o samym
serwisie: „Tak, tak, wszyscy się strasznie cieszą” (rosną reakcje, sypią się „Gratulacje!”), „Czekaj, ten wpis jest najlepszy” (przewinięcie
do wpisu Grażyny i wjazd w jej zdjęcie), refren 2 „wielkie zasięgi” (licznik wyświetleń do 1 254 302) i „A pod spodem cisza” (pusta sekcja
komentarzy), po bridge'u prosty wpis „Robię swoje.”, outro „miłego scrollowania” (przewijanie feedu) i statystyki na koniec.
Obsada (oryginalne lalki): Henio Kawka (narrator, cały wokal prowadzący), Grażyna Gratka, Prezes Bogumił Łaskawiec, Tadek Nowadroga,
Mirek Szacun, Kasia Kejs, Chór Zasięgów (8 lalek: 4 panów w przedrefrenach, panie dochodzą w refrenach – liczebność tylko rośnie).
Chór śpiewa to, co w nagraniu jest w stemie chórków (dublowania, „trochę jak męka”, wtrącenie, wokalizy) – lista w `scenariusz.md`.
Taniec nie jest głównym językiem: gesty ilustrują słowa (łyk kawy na „kawa”, ręka na żuchwie na „szczęka”, wyuczony uśmiech
i salut do czoła na „uśmiech wyuczony, rzut na czoło”, stempel „RESTRUKTURYZACJA” na „bruk”, aureola na „świętym”…), a rytmiczne
podrygi pojawiają się w refrenach (reakcje na patykach w górę na „raz” taktu, dociągnięte do prawdziwej stopy).

## 4. Realizacja obrazu
* **Renderer 2D z perspektywą warstw (skia-python), bezstanowy**: każda klatka liczona wyłącznie z czasu t = n/30 (`src/video/render.py`).
* **Lalki** (`puppet.py`, `cast.py`): głowa jako superelipsa przecięta linią ust dokładnie w kącikach (zawias w kącikach), wnętrze ust
  i język, oczy-piłeczki, powieki, nos z pianki, futro z kosmyków, faktura filcu, dłonie na prętach; ciało od pasa w górę zza krawędzi
  sceny. **v3 – bryła**: wspólne cieniowanie całej głowy (cień własny po stronie przeciwnej do reflektora, miękki odblask, kontrświatło
  na krawędzi), cylindryczne cieniowanie korpusu i spadek światła w dół; korpus sięga głęboko pod krawędź sceny, więc przy kamerze
  z góry paralaksa nie odsłania jego spodu („brak nóg”).
* **Rekwizyty na drążkach** (v3): tabliczki, maski, wachlarze reakcji, gwiazdki, łza mają drążek, który przechodzi **przez zaciśniętą
  pięść** (palce i kciuk rysowane na drążku), a tabliczka jest nad dłonią; kostki bruku to kamienie w garści. Rekwizyty nie zasłaniają
  ust w trakcie śpiewu (łyk kawy przed wersem, telefon z boku).
* **Ruch** (v3): gesty jak u lalkarza – poza trzymana do ostatniej chwili, potem szybki ruch (0,12–0,3 s) z 8% przestrzałem i powrotem;
  **ekspresja śpiewu z sylab**: kiwnięcie głowy na każdej akcentowanej sylabie (siła = otwarcie ust), na długich nutach głowa w górę,
  przymknięte oczy i uniesione brwi; **taniec tylko w refrenach i finale** (krok w bok co 2 bity, sprężynowanie na stopie);
  akcenty (kiwnięcia, przysiady, błyski) na prawdziwych uderzeniach stopy/werbla.
* **Kamera** (v3, `timeline.py`): kadrowanie **względem postaci** – plan wybierany jak w studiu TV (CU zbliżenie twarzy, MCU do piersi,
  MS do pasa, MLS/LS grupowe, WS teatralny), kamera śledzi postaci i płynnie zmienia plan między kluczami (najazd, odjazd, jazda);
  w planach CU/MCU/MS dół kadru nie schodzi poniżej pasa lalki, więc nie widać krawędzi sceny pod nią. Skład grupy w kadrze ustalany dla
  całego ujęcia (kadr nie skacze, gdy ktoś się wynurza). Cięcia na początkach wersów lub na „raz” taktu, każdy refren ma inne ujęcia.
* **Przestrzeń i światło** (v3, `compose.py`, `post.py`): **głębia ostrości** liczona z odległości kamery (tło i dekoracje rozmyte
  w zbliżeniach, portal na pierwszym planie lekko nieostry), **cienie sylwetek** lalek (głowa z oczami, korpus, ręce, rekwizyty) rzucone
  na dekorację – przesunięte od reflektora i rozmyte zależnie od odległości od ściany, cień warstwy środkowej dekoracji na ścianie,
  gradacja (krzywa S, +8% nasycenia), słabsza halacja i zmiękczenie niż w v2, ziarno, winieta.
* **Napisy jako scenografia** (`signs.py`, `timeline.py`): tablice z tektury na sznurkach, litery na froncie sceny, **podświetlone
  litery na froncie podestu chóru** (v3), neon portalu, dymki do kwestii mówionych, karton pisany markerem (bridge). Każdy wers ma jedno
  stałe miejsce w świecie, wybierane automatycznie z ~1000 kandydatów (także zakotwiczonych w kadrze ujęcia), tak by napis był w kadrze
  przez cały czas trwania (także po cięciu) i nie nachodził na postacie, ważne rekwizyty ani inne napisy; słowa pojawiają się
  w chwili zaśpiewania (czasy z nowego dopasowania). Fonty świata lalek (v3, OFL, Google Fonts, polskie znaki sprawdzone):
  Titan One (tablice), Cherry Bomb One (front sceny i podestu), Rammetto One (portal), Sigmar One (duże napisy), Kalam (dymki),
  Caveat Brush (marker), Shrikhand (tytuł); w świecie serwisu bez zmian (Inter).
* **Klon LinkedIna** (`linkedin_clone/`): HTML/CSS/JS od zera (Inter OFL, własne ikony SVG, awatary = portrety lalek). Stany strony
  przechwytywane Playwrightem, w teledysku składane z przewijaniem, „kamerą” na ekranie, filmem ze sceny na żywo w ramce posta,
  licznikami rosnącymi klatka po klatce i pisaniem słowo po słowie.
* **Render** (`src/render_all.py`, `src/assemble.py`): kawałki po 300 klatek, 4 procesy równolegle (x264 CRF 14), sklejenie bez
  rekompresji, końcowe kodowanie H.264 yuv420p (dwa przebiegi, ≤ 100 MB dla GitHuba) + AAC 320 kb/s z całego MP3 (bez filtrów i cięć).
  Każda wersja renderowana z zamrożonej kopii kodu (`build/vN/src`).

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
* **Granice sylab**: czasy słów potwierdzają cztery niezależne metody (2.4), ale granice pojedynczych sylab w szybkich frazach
  i trzymanych nutach pochodzą z jednego narzędzia (MFA, model mowy, nie śpiewu) – możliwe błędy rzędu kilkudziesięciu ms.
  Trzy słowa (angielskie „case”, „cringe” i „Że” w 55,9 s) nie zostały pewnie rozpoznane przez żaden model; ich pozycja pochodzi
  z wymuszonego dopasowania.
* **Podział Henio / chór** wynika ze stemów; tam, gdzie chór dubluje Henia cicho, mógł zostać pominięty (chór rusza wtedy ustami
  tylko na wyraźnie słyszalnych słowach).
* **Tekst a nagranie**: w refrenie 1 (wers 6) śpiewane jest „Puste zasięgi”, a nie „Wielkie zasięgi” – napis pokazuje wersję
  śpiewaną; „hej” z tekstu w refrenach 1–2 nie ma w nagraniu, więc nie ma go też w obrazie (napis i okrzyki tylko w refrenie 3 i finale).
  Jeśli ma być zgodnie z kartką tekstu – to jedna zmiana w danych.
* **Modele mowy pobrane z mniej oczywistych źródeł**: Whisper small z rejestru npm (paczka osoby trzeciej; suma SHA-256 zgodna z jej
  własną deklaracją, transkrypcja sensowna) – użyty tylko do kontroli, nie do czasów w filmie. Omnilingual, Parakeet i MFA pochodzą
  z oficjalnych wydań projektów.
* **Napisy**: w kilku ciasnych kadrach napis jest mały albo ma ~80–90% widoczności na brzegu kadru w ostatnich chwilach wersu
  (lista w `checks/verify_sync.json`, pole `signs.placement`).
* **Kompresja**: 3200 kb/s, żeby zmieścić się w 100 MB na GitHubie. Głębia ostrości i ziarno lepiej wyglądałyby w wyższej
  przepływności – kawałki CRF 14 są w `build/v3/chunks` (`python3 src/assemble.py build/v3/chunks <plik> --crf 16`).
* **Klon LinkedIna**: zgodnie z prośbą odtwarza wygląd serwisu 1:1, w stopce jest linijka „LinkedIn Corporation © 2026” jak
  w oryginale (obok dopisek, że to klon; w napisach końcowych „serwis w kadrze jest fikcyjny”). Przed publikacją warto zdecydować,
  czy zostawić nazwę i stopkę.
* **Interpretacje**: finał (wszyscy wracają na scenę) i scena „pod spodem” (widok od strony lalkarzy) to moje odczytanie tekstu.

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

### 7.3 v3 – poprawki po uwagach autora do v2

#### 7.3.1 Synchronizacja z dźwiękiem
* Uwaga: „synchronizacja z audio leży”.
* Przyczyna (sprawdzona transkrypcją Omnilingual i porównaniem narzędzi, 2.4): dopasowanie v2 było zrobione bez modelu rozpoznawania
  mowy; w zwrotce 2b wszystkie wersy były przesunięte o jeden (−2,7 … −3,4 s), wtrącenie „Wywalili na bruk!” było 2,9 s za późno,
  „Mocne zasięgi” w refrenie 1 o 0,9 s za późno; 14 słów różniło się o > 0,5 s, a 41 w ogóle nie dało się znaleźć w ±1,5 s.
  Chór otwierał usta na każde zdarzenie w stemie chórków (także na przesłuch Henia), a Henio śpiewał partie, które w nagraniu
  śpiewa tylko chór („trochę jak męka”); „hej” w refrenach 1–2 było tam, gdzie go nie ma.
* Poprawka: pięć narzędzi (Omnilingual CTC, MFA, Whisper, Parakeet, Silero VAD), wymuszone dopasowanie osobno na stemach Henia i chóru,
  fuzja z fonemów MFA; podział partii Henio / chór / razem; wariant tekstu sprawdzany akustycznie; „hej” tylko tam, gdzie jest w stemie.
* Sprawdzenie: zgodność z MFA 89% słów w ±100 ms, z Parakeetem 0 słów > 0,5 s (tabela w 2.4); liczby ust w sekcji 5.

#### 7.3.2 Tabliczki trzymane na drążkach
* Uwaga: „muppety nie trzymają tabliczek poprawnie – po to mają tyczki”.
* Przyczyna: drążek szedł od dłoni w dół, tabliczka siedziała tuż nad dłonią i była rysowana na wierzchu dłoni.
* Poprawka: tabliczka nad dłonią, drążek przez zaciśniętą pięść (palce i kciuk na drążku), rysowanie: rekwizyt → pięść; bruk = kamienie
  w garści. Sprawdzenie: zbliżenia klatek z maskami, wachlarzami, tabliczkami „3 OPINIE”, „Ogromny szacun!”, „Cieszę się z nowej drogi!”.

#### 7.3.3 „Widać, że postaci nie mają nóg”
* Przyczyny: (1) Henio do 99,7 s „dziedziczył” y = −40 z późniejszej sceny (pierwszy klucz y był dopiero w raju), więc spód korpusu
  wypadał równo z krawędzią sceny; (2) dla lalek dalej od krawędzi kamera z góry odsłaniała spód korpusu przez paralaksę;
  (3) plany średnie pokazywały pod lalką pas sceny i pustą ścianę.
* Poprawka: bazowe y = 0 od początku dla wszystkich ról; korpus sięga 320 jednostek pod krawędź; nowa kamera – w planach do pasa dół
  kadru nad krawędzią sceny. Sprawdzenie: arkusze środków wszystkich 53 ujęć sceny.

#### 7.3.4 Animacje, ekspresja śpiewu i taniec
* Uwaga: „animacje kuleją”, ruchy „bardziej ekspresyjne w śpiewie i tańcu”.
* Przyczyna: pozy przechodziły płynnie przez cały odstęp między kluczami (wrażenie pływania), ruch głowy nie zależał od śpiewu.
* Poprawka: ruch lalkarski (trzymanie pozy, szybki ruch z przestrzałem 8%); kiwnięcia na akcentowanych sylabach, długie nuty (głowa
  w górę, przymknięte oczy), brwi z głośnością; taniec w refrenach (krok co 2 bity, sprężynowanie na stopie).

#### 7.3.5 Praca kamery
* Uwaga: „praca kamery do poważnej analizy i poprawy”.
* Analiza v2: wszystkie 53 ujęcia sceny miały ręcznie wpisane pozycje kamery, niezależne od tego, gdzie stoją postacie; 23 z nich
  w jakiejś fazie pokazywały cały portal (płasko, postaci małe), plany średnie odsłaniały krawędź sceny pod lalkami.
* Poprawka: kadrowanie względem postaci (rozdział 4), skład grupy stały w ujęciu, przejścia między planami w obrębie ujęcia.
* Sprawdzenie: arkusze środków ujęć; ruch kadru między klatkami w ujęciach: najwyżej 44 px/klatkę (zamierzone przejście z Henia na chór),
  pozostałe ≤ 36 px/klatkę.

#### 7.3.6 Wygląd: przestrzeń, cienie
* Uwaga: „wszystko płaskie”, „popracować nad cieniem”.
* Poprawka: bryła głów i korpusów, cienie sylwetek na dekoracji, cień dekoracji na ścianie, głębia ostrości zależna od kamery,
  gradacja (rozdział 4). Sprawdzenie: klatki porównawcze (kuchnia, konferencja, chór, raj, bridge, refren 3).

#### 7.3.7 Usta: półotwarcia
* Uwaga: „nie tylko pełne otwarcia, ale też półotwarcia gęby”.
* Poprawka: otwarcie każdej sylaby z samogłoski, głośności, długości i akcentu (0,22–1,0), dołki między sylabami zamiast pełnego
  zamknięcia (pełne tylko przed m/b/p i w przerwach), zaokrąglenie dla o/u. Sprawdzenie: ciąg 16 klatek „wielkie zasięgi” (68,0 s) –
  szerokie „wiel”, domknięcie, półotwarte „kie”; liczby w sekcji 5.

#### 7.3.8 Fonty w świecie lalek
* Poprawka: siedem stylizowanych krojów OFL z Google Fonts (lista w rozdziale 4, pliki i licencje w `fonts/`); świat serwisu bez zmian.

#### 7.3.9 Napisy w nowych kadrach
* Problem (wyszedł po zmianie kamery): w ciaśniejszych kadrach 38 z 47 napisów wypadało częściowo lub całkiem poza kadr.
* Poprawka: kolizje liczone osobno dla głowy, korpusu i dłoni z rekwizytem; kandydaci zakotwiczeni w kadrze ujęcia; litery na froncie
  podestu chóru; napis oceniany przez cały czas trwania (także po cięciu) i bez kolizji z innymi napisami; napis gaśnie, gdy zaczyna się
  następny wers. Wynik: 39 z 47 napisów w pełni widocznych i bez kolizji, pozostałe ≥ 81% widoczności (szczegóły w sekcji 5).
