# Raport: teledysk „Puste zasięgi” (Paweł Kuraś)

> Stan: **wersja v4** (`final/music-video.mp4`). Poprzednie wersje: `archive/v1/`, `archive/v2/`, `archive/v3/`. Wyniki sprawdzeń poniżej dotyczą v4.
> Nie słuchałem ani nie oglądałem filmu – wszystko niżej to pomiary liczbowe i obejrzane pojedyncze klatki / arkusze klatek.

## 1. Co powstało

| Plik / folder | Zawartość |
|---|---|
| `final/music-video.mp4` | teledysk 1920×1080, 30 kl./s, H.264 yuv420p, AAC; autor w metadanych i napisach: Paweł Kuraś |
| `scenariusz.md` | obsada (oryginalne lalki) i scenariusz z czasami |
| `linkedin_clone/` | samodzielny klon feedu (HTML/CSS/JS, własne ikony SVG); po otwarciu `index.html` w poście Henia odtwarza się `final/music-video.mp4` |
| `analysis/` | wyniki analizy muzyki (tekst, bity, części, dopasowanie słów) + wykresy kontrolne |
| `src/` | cały kod: analiza (`a01…a12`; v3: `a20…a25` – modele mowy, dopasowanie, fuzja), renderer (`src/video/`), render równoległy, montaż, weryfikacja |
| `checks/` | arkusze klatek, stopklatki, wyniki weryfikacji (`verify_file.json`, `verify_sync.json`, `exposure.json`) |
| `fonts/` | czcionki OFL użyte w obrazie i w klonie + pełny tekst licencji |
| `archive/` | poprzednie wersje filmu: `v1/`, `v2/`, `v3/` (nic nie jest kasowane; w każdej `NOTES.md` z uwagami do tej wersji) |
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
v4 dokłada trzy powroty do serwisu: „A w komentarzu: „Ogromny szacun”” (zdjęcie z konferencji we wpisie prezesa = zatrzymany kadr
sceny, pod nim pojawia się komentarz Mirka, „Ogromny szacun!” wpisuje się razem ze śpiewem), „„Cieszę się z nowej drogi” — czytam
bez tchu” (wpis Tadka z ramką #OpenToWork, Henio pisze to do Tadka na czacie) i „Ktoś sprzedaje się za trzy opinie” (profil
z sekcją „Rekomendacje”: trzy rekomendacje pojawiają się na słowa, licznik 0 → 3). „Studio w drewnie” to typowe studio podcastowe.
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
  całego ujęcia (kadr nie skacze, gdy ktoś się wynurza). Cięcia na początkach wersów lub fraz albo na „raz” taktu, każdy refren ma inne ujęcia.
  **v4**: kadr obejmuje wszystko, co w danej chwili opowiada historię – postaci, **trzymane tablice i karty** (obrys rekwizytu liczony
  z rastra), **rekwizyty sceny** (scenki z życia, zwój, baner AWANS, chmurka, flipchart, rekomendacje, aureola, „Robię swoje.”, trąbka,
  sztaluga, laptop, marynarka) i **napis wersu** (tablica wisi obok postaci, a kamera kadruje je razem). Kadr dopasowuje się do tych
  prostokątów (każdy na swojej głębokości), nie wychodzi poza otwór sceny, jeśli treść się mieści, a głowy innych lalek z pierwszego
  planu są w kadrze całe albo wcale (automatyczne objęcie albo przesunięcie kadru). Ujęcia, w których kadry kluczowe wyszły
  identyczne, mają powolny najazd (5%).
* **Przestrzeń i światło** (v3, `compose.py`, `post.py`): **głębia ostrości** liczona z odległości kamery (tło i dekoracje rozmyte
  w zbliżeniach, portal na pierwszym planie lekko nieostry), **cienie sylwetek** lalek (głowa z oczami, korpus, ręce, rekwizyty) rzucone
  na dekorację – przesunięte od reflektora i rozmyte zależnie od odległości od ściany, cień warstwy środkowej dekoracji na ścianie,
  gradacja (krzywa S, +8% nasycenia), słabsza halacja i zmiękczenie niż w v2, ziarno, winieta.
  **v4**: plamy reflektorów, snopy i błyski w trybie „screen” (rozjaśniają, ale nie przepalają), halacja tylko od naprawdę jasnych
  partii i dodana **przed** krzywą tonalną, krzywa z miękkim „ramieniem” w światłach (biel → ok. 0,93, z fakturą), ciemniejsze tło
  dekoracji; ziarno drobne (1 piksel tekstury = 1 piksel obrazu) i słabe (2× mniejsze niż w v3), zmienia się co 2 klatki.
  **Strona serwisu jest czysta** – bez ziarna, blasku, winiety i gradacji; obróbka „show” jest tylko w obrazie filmu w poście
  (i w pełnych ujęciach sceny), więc przejście kamery z posta do sceny jest ciągłe.
* **Napisy jako scenografia** (`signs.py`, `timeline.py`): tablice z tektury na sznurkach, litery na froncie sceny, **podświetlone
  litery na froncie podestu chóru** (v3), neon portalu, dymki do kwestii mówionych, karton pisany markerem (bridge). Każdy wers ma jedno
  stałe miejsce w świecie; słowa pojawiają się w chwili zaśpiewania (czasy z dopasowania). **v4**: tablica/dymek stoi **obok postaci**
  (z boku na wysokości głowy, wyżej albo nad głową – kandydaci wokół śpiewającego i wokół całej grupy w kadrze), wybór bez kolizji
  z postaciami, trzymanymi rekwizytami, rekwizytami sceny i innymi napisami, tylko w otworze sceny; kamera obejmuje napis. Wielkość
  pola z rzeczywistego obrysu glifów (polskie ogonki i kreski) + zapas na „wyskok” słowa (10%); tekst łamany na 1–3 wyważone linijki,
  w razie potrzeby mniejszy krój – nigdy poza pole. Tablica: gładka tektura z delikatną fakturą, ciemniejszy rant, oczka na sznurki,
  miękki cień, kolory zależne od dekoracji, bez obwódki. Dymek: jeden kontur (prostokąt i ogonek złączone operacją na ścieżkach),
  ogonek wskazuje usta mówiącego, dymek rośnie od ogonka. Napis kończący się na cięciu znika razem z ujęciem (bez wygaszania). Fonty świata lalek (v3, OFL, Google Fonts, polskie znaki sprawdzone):
  Titan One (tablice), Cherry Bomb One (front sceny i podestu), Rammetto One (portal), Sigmar One (duże napisy), Kalam (dymki),
  Caveat Brush (marker), Shrikhand (tytuł); w świecie serwisu bez zmian (Inter).
* **Klon LinkedIna** (`linkedin_clone/`): HTML/CSS/JS od zera (Inter OFL, własne ikony SVG, awatary = portrety lalek). Stany strony
  przechwytywane Playwrightem, w teledysku składane z przewijaniem, „kamerą” na ekranie, filmem ze sceny na żywo w ramce posta,
  licznikami rosnącymi klatka po klatce i pisaniem słowo po słowie (pole wiadomości zawija tekst jak przeglądarka). v4: komentarze pod
  wpisem prezesa (`?prezes=1`) i strona profilu z sekcją „Rekomendacje” (`?profile=1&recs=0…3`).
* **Studio podcastowe** (v4, `stage.py`, `props.py`): beżowe zasłony w fałdy, panel z drewnianych listew za prowadzącym, neon
  „podcast”, dwa regały (książki, świecąca lampka, świece, aparat, pomarańczowa tuba LED, rośliny, pnącze), lampy podłogowe z białym
  abażurem, duże rośliny w donicach, stół z jasnego drewna z kubkami i mikrofony na ramionach – z boku ust, żeby nie zasłaniały ruchu
  szczęki. Henio prowadzi, dwóch panów z chóru to goście z maskami uśmiechu.
* **Render** (`src/render_all.py`, `src/assemble.py`): kawałki po 300 klatek, 4 procesy równolegle (x264 CRF 14), sklejenie bez
  rekompresji, końcowe kodowanie H.264 yuv420p (dwa przebiegi, ≤ 100 MB dla GitHuba) + AAC 320 kb/s z całego MP3 (bez filtrów i cięć).
  Każda wersja renderowana z zamrożonej kopii kodu (`build/vN/src`).

## 5. Jak sprawdziłem wersję v4
Skrypty: `src/verify.py` (plik) i `src/verify_sync.py` (synchronizacja liczona z tych samych funkcji, z których renderowane są klatki).
Wyniki: `checks/verify_file.json`, `checks/verify_sync.json`, `checks/sheets/` (arkusze co 4 s), `checks/stills/` (45 stopklatek).

**Plik** (`final/music-video.mp4`)
* Pełne dekodowanie `ffmpeg -f null`: **0 błędów**.
* Obraz: H.264 High, yuv420p, 1920x1080, 30/1 kl./s, **6482 klatek = oczekiwane 6482**, 216.067 s.
* Dźwięk: AAC 48000 Hz, 2 kanały, 212.0 s; plik 95.03 MB.
* Metadane: tytuł „Puste zasięgi”, artist/composer „Paweł Kuraś”, komentarz „Teledysk: Paweł Kuraś”; autor także w napisach końcowych.
* **Przesunięcie dźwięku względem MP3: 0, 0, 0, 0, 0, 0, 0, 0 próbek** w 8 miejscach (5, 30, 61, 100, 140, 170, 200, 210 s),
  korelacja 0.9996–0.9999; na końcu 512 próbek ciszy z dopełnienia ramki AAC; SNR 36.09 dB (strata AAC).

**Synchronizacja**
* Usta Henia: **484 z 484 sylab ma własny szczyt otwarcia**, 53/53 wersów
  dokładnie „sylaba = szczyt”; 62.6% szczytów to półotwarcia (< 0,7); usta otwarte w ciszy wokalu: 2.81% takich klatek.
* Usta chóru: **140 z 140 sylab** tekstu śpiewanego przez chór ma własny szczyt; 12 wokaliz bez słów; „hej” w 182.43, 185.66 s.
* Początki słów tam, gdzie gra stem: Henio 99.2% z 265 (wyjątki: „kochani” 5.28 s, „fanfar” 162.17 s),
  chór 100.0% z 75.
* Zgodność dopasowania z niezależnymi narzędziami – tabela w 2.4.
* Akcenty ruchu: 183 szczytów, **100.0% w ±1 klatce od uderzenia stopy/werbla** (mediana 8.8 ms);
  błyski: 10, 100.0% w ±2 klatkach od werbla lub „hej”.
* Cięcia: **60/60 na początku wersu (lub zdania w kwestii mówionej) albo na „raz” taktu**. Ujęcia bez ruchu kamery: 0.
* Napisy (co 2. klatka ujęć sceny, 1914 sprawdzeń): największe nachodzenie napisu na postać **19.4%**
  powierzchni napisu ([67.8, [4, 2], 'Henio Kawka']; prostokąty: głowa, korpus, dłoń z rzeczywistym obrysem trzymanego rekwizytu), najmniejsza widoczność napisu w kadrze 98% ([163.87, [10, 4]]);
  41 z 45 napisów w pełni widocznych i bez kolizji przez cały czas trwania.
* Trzymane nuty (głos trwa ≥ 0,4 s po szczycie sylaby; koniec głosu z obwiedni stemu): Henio 41 nut – usta otwarte
  średnio przez **100.0%** czasu dźwięku, chór 37 nut – 100.0%.
* Tekst w polu tablic i dymków (29 napisów): **wszystkie mieszczą się** razem z powiększeniem
  słowa w chwili zaśpiewania; najmniejszy zapas 16.8 px w poziomie i 13.7 px w pionie (obrys glifów z polskimi znakami).
* Tablice i dymki w otworze sceny (nie za portalem): 100.0% sprawdzonych klatek.
* Kadr (co 3. klatka ujęć sceny, 1705 klatek): głowa lalki pierwszego planu ucięta krawędzią w **39 klatkach**
  (2.3%; prawie wyłącznie tłum w refrenie 3, 171.7–184.9 s; lalki w trakcie
  wynurzania/wejścia nie są liczone); kadrowana postać niewidoczna: 4 klatek (97.1, 99.7, 113.3, 147.9 s – wynurzanie na cięciu);
  ważne rekwizyty ujęcia (scenki z życia, zwój, baner, flipchart, „Robię swoje.”…) widoczne w ≥ 90%: 359/359 próbek.
* Ekspozycja (`src/verify_exposure.py`, `checks/exposure.json`; ujęcia sceny, 10 kl./s): przepalone piksele (kanał ≥ 250) średnio
  **0.12%** (v3: 13.95%), 95. percentyl 0.3% (v3: 43.96%), najgorsza klatka 53.27%
  (v3: 59.86%); klatek z > 5% przepaleń: 1 z 1737 (v3: 1307 z 1820).
  (jedyna próbka > 5% – 163,9 s – wypada na cięciu do białej strony serwisu; klatka sceny przed cięciem jest bez przepaleń).
* Chór: liczebność w refrenach nie spada; w układzie grupowym 0 par nachodzących na siebie.

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
* **Kadry w tłumie (refren 3)**: lalki stoją ramię w ramię, więc w planach grupowych sąsiad bywa ucięty krawędzią kadru (liczby
  w sekcji 5); objąłem go albo przesunąłem kadr tam, gdzie wystarczało ≤ 30% oddalenia lub ≤ 15% przesunięcia – dalej uznałem
  to za naturalne dla ujęcia tłumu.
* **Napis przy postaci**: w 67,8 s dłoń Henia w szerokim geście wchodzi pod tablicę „Puste zasięgi, wielkie zasięgi” (19% pola
  tablicy w teście prostokątów) – na klatce wygląda to jak wskazanie napisu, więc zostawiłem.
* **Kompresja**: 3200 kb/s, żeby zmieścić się w 100 MB na GitHubie. Głębia ostrości lepiej wyglądałaby w wyższej
  przepływności – kawałki CRF 14 są w `build/v4/chunks` (`python3 src/assemble.py build/v4/chunks <plik> --crf 16`).
* **Rekomendacje i komentarze w serwisie** (v4) są wymyślone dla żartu (np. rekomendacja od własnego „konta firmowego”); postaci
  fikcyjne, jak cała reszta.
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
* Sprawdzenie: arkusze środków ujęć; ruch kadru między sąsiednimi klatkami w ujęciach najwyżej 33,5 px/klatkę (płynne jazdy, bez skoków);
  każde ujęcie sceny ma ruch kamery (test „ujęcia bez ruchu”: 0).

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
  następny wers; gęste próbkowanie (co 0,2 s) – pierwsza wersja v3 przegapiła ruch ręki Henia i napis „Poranna kawa…” nachodził na nią
  w 37,6% (17,27 s), po poprawce i przerenderowaniu 13 z 22 kawałków: 42 z 47 napisów w pełni widocznych i bez kolizji, największe
  nachodzenie 7,0% (zgrubne prostokąty), najmniejsza chwilowa widoczność 44% na końcu wersu (sekcja 5).

### 7.4 v4 – poprawki po uwagach autora do v3

#### 7.4.1 Prześwietlenia
* Uwaga: „jest prześwietlone w niektórych momentach”.
* Pomiar v3 (cały plik, 10 kl./s): w ujęciach sceny średnio 14% pikseli przepalonych do bieli (kanał ≥ 250), w kuchni (17–23 s)
  i u Grażyny (84–86 s) ponad 50% kadru.
* Przyczyna: trzy rzeczy dodawane do obrazu (plama reflektora na postaci, halacja, błysk flesza) w trybie „plus” w 8 bitach, halacja
  dokładana już po krzywej tonalnej; jasna ściana dekoracji + plama + halacja = obcięcie do 255.
* Poprawka (`post.py`, `gfx.py`, `compose.py`, `timeline.py`): światła w trybie „screen”, halacja tylko od naprawdę jasnych partii
  i liczona przed krzywą tonalną, krzywa z miękkim ramieniem w światłach, słabsze plamy, ciemniejsze tło dekoracji, łagodniejsze flesze.
* Sprawdzenie: te same klatki przed / po: 52–59% → 0% przepaleń, 99. percentyl jasności ≤ 233; cały plik – sekcja 5.

#### 7.4.2 Strona serwisu bez ziarna, mniejsze ziarno
* Uwaga: prawdziwy LinkedIn bez ziarna i „analogowości”; ziarno za duże (kompresja serwisu).
* Przyczyna: na przebitkach obróbka „filmowa” szła na całą klatkę (strona też), ziarno miało 2× powiększone piksele i siłę 0,12.
* Poprawka (`render.py`, `linkedin.py`, `post.py`): strona serwisu bez żadnej obróbki; wygląd show tylko w obrazie filmu w poście
  i w ujęciach sceny; ziarno 1:1 piksel, siła 0,055.
* Sprawdzenie: klatki 44,3 / 92,6 / 104,9 s (serwis – czysty), 16,2 / 114,6 s (scena).

#### 7.4.3 Tablice: czerwona obwódka, tekst poza polem
* Przyczyna: stała wewnętrzna obwódka w kolorze `#b5452b`; wielkość tablicy liczona z wielkości czcionki, a nie z obrysu liter,
  przy „wyskoku” słowa o 22% (zapas był mniejszy) słowo przy brzegu wychodziło poza pole; samotny myślnik mógł zacząć nową linijkę.
* Poprawka (`signs.py`): bez obwódki (gładka tektura, ciemniejszy rant, oczka, miękki cień); pole z obrysu glifów + zapas na
  „wyskok” (teraz 10%); 1–3 wyważone linijki, w razie potrzeby mniejszy krój; znaki interpunkcyjne doklejone do słowa.
* Sprawdzenie: test tekstu w polu (sekcja 5) – wszystkie tablice i dymki z zapasem; klatki 16,2 i 45,8 s.

#### 7.4.4 Dymki „poskładane z elementów”
* Przyczyna: prostokąt i trójkątny ogonek rysowane jako osobne kształty, każdy z własnym obrysem.
* Poprawka: jeden kontur (suma ścieżek), wklęsłe boki ogonka, ogonek wskazuje usta mówiącego, delikatny gradient, jeden obrys.
* Sprawdzenie: klatki 5,5 i 149,5 s.

#### 7.4.5 Napisy w złych miejscach i poza kadrem
* Przyczyna: w v3 miejsce napisu wybierane w kadrze z połowy wersu, a kamera w trakcie wersu robiła najazd – napis uciekał na brzeg
  albo poza kadr (np. „Poranna kawa” w rogu, „Z pokorą informuję” daleko w prawym górnym rogu); część kandydatów leżała za portalem.
* Poprawka: napis kotwiczony przy postaci (rozdział 4) i **kamera kadruje postać razem z napisem**; tylko w otworze sceny.
* Sprawdzenie: widoczność napisów w kadrze i nachodzenie – sekcja 5; arkusze 3 klatek na każde ujęcie (początek, środek, koniec).

#### 7.4.6 Praca kamery, „A potem pięć scenek z życia”
* Problem: kamera kadrowała tylko lalki; scenki wisiały daleko w tle na całej szerokości sceny (±940), więc w planie Grażyny było
  widać ich rogi; ucięte karty trzymane w rękach (wpis Henia, wpis Grażyny), puste kadry na końcu ujęć (postaci chowały się przed
  cięciem, a błąd w zejściu „bez animacji” zostawiał je jeszcze 0,45 s w następnej dekoracji), głowy ucięte dolną krawędzią.
* Poprawka: kadr z postaci + trzymanych rekwizytów + rekwizytów sceny + napisu (rozdział 4); scenki w rzędzie nad Grażyną,
  zwój obok; zejścia na cięciach; głowy całe albo wcale; kadr w otworze sceny; nadmiar wysokości w planach grupowych po połowie
  nad i pod grupą; powolny najazd w ujęciach bez zmiany planu; trzy-ujęcie Henio–Tadek–prezes na drodze.
* Sprawdzenie: arkusze 3 klatek (początek, środek, koniec) dla wszystkich 61 ujęć – 6 przeglądów z poprawkami między nimi; test kadru w sekcji 5.

#### 7.4.7 Częściej „prawdziwy” serwis
* Nowe przebitki: 42,6–45,1 s (komentarz „Ogromny szacun!” pod wpisem prezesa, zdjęcie = zatrzymany kadr konferencji bez napisów),
  90,1–93,1 s (wpis Tadka, Henio pisze wers do Tadka na czacie), 102,9–105,8 s (profil z rekomendacjami). Razem z dotychczasowymi:
  10 przebitek, 38,3 s serwisu (v3: 7 przebitek, 29,9 s).
* Sprawdzenie: klatki 44,3 / 92,6 / 104,9 s.

#### 7.4.8 „Studio w drewnie” jak typowe studio podcastowe
* Poprawka: nowa dekoracja i stół z mikrofonami (rozdział 4); przedrefren 2 nagrywany „jak podcast” – na słowach „studio w drewnie”
  odjazd na całą dekorację.
* Sprawdzenie: klatki 114,6 i 118,7 s.

#### 7.4.9 „Trzy opinie” = rekomendacje w serwisie
* Poprawka: w serwisie profil z sekcją „Rekomendacje” (trzy rekomendacje na słowa „sprzedaje / się / trzy”); na scenie metka
  „CENA: 3 rekomendacje” i trzy kartki-rekomendacje na patykach („Wizjoner!”, „Szacun!”, „Polecam!”) zamiast metki „3 OPINIE” i gwiazdek.
* Sprawdzenie: klatki 104,9 i 107,5 s.

#### 7.4.10 Usta zamykały się za wcześnie na trzymanych nutach
* Uwaga (w trakcie renderu v4): przy długich frazach typu „eeeee” pacynki za szybko zamykają usta.
* Przyczyna: koniec sylaby brany z dopasowania modelem mowy (MFA), który kończy samogłoskę tam, gdzie kończyłaby się w mowie –
  w śpiewie głos trwa dalej. Pomiar: z 54 trzymanych nut Henia (głos ≥ 0,4 s po szczycie sylaby) 20 miało usta otwarte przez
  mniej niż 95% czasu dźwięku, np. „gi” w finale (197,5 s) – usta zamknięte, a głos trwa jeszcze 3,7 s; „gest” 125,0 s – 1,8 s.
* Poprawka (`engine.py`): koniec otwarcia = koniec dźwięku w stemie (poziom nie niżej niż 9 dB pod szczytem sylaby i nad bramką,
  najdalej 40 ms przed następną sylabą); na długiej nucie szczęka lekko przymyka się w pierwszych 0,4 s i dalej trzyma; ta sama
  sylaba z dwóch źródeł (końcowe „HEJ” chóru) łączona w jedną.
* Sprawdzenie: test „trzymane nuty” w `src/verify_sync.py` – Henio: średnio 85,5% → 95,4% czasu dźwięku z otwartymi ustami
  (przed poprawką liczone na tych samych danych), chór 96,9% → 98,5%; wynik na pliku – sekcja 5.

#### 7.4.11 Reakcje jak w serwisie
* Uwaga (w trakcie renderu v4): reakcje (łapka, serduszko…) mają wyglądać jak w serwisie – i na patykach lalek, i w klonie.
* Przyczyna: w klonie były to kolorowe kółka z białym prostokątem/rombem, na patykach – uproszczone białe kształty.
* Poprawka (`src/video/reactions.py`): jeden zestaw sześciu ikon SVG narysowanych od nowa na wzór reakcji serwisu – Lubię to
  (niebieskie koło, łapka z mankietem), Gratulacje (zielone, klaszczące dłonie), Wsparcie (fioletowe, dłoń z sercem), Uwielbiam
  (koralowe, serce), Wnikliwe (żółte, żarówka), Zabawne (turkusowe, roześmiana buzia). Te same pliki są w klonie
  (`linkedin_clone/assets/r_*.svg`, liczniki reakcji pod wpisami) i na tekturowych krążkach, które trzyma chór.
* Sprawdzenie: zrzut klonu (liczniki pod wpisem Henia) i klatka 64,5 s (chór z reakcjami).
