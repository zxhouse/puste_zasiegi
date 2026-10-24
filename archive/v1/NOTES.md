# Wersja v1 (archiwum)

`music-video.mp4` — pierwsza pełna wersja teledysku (6482 klatki, 216,067 s, 1920×1080, 30 kl./s, H.264 High yuv420p, AAC 48 kHz stereo, 94,82 MB, kodowanie CRF).
Kod, z którego powstała, był zamrożony w `build/v1/src` (katalog `build/` nie trafia do repozytorium; ten sam stan kodu jest w historii gita przed commitem z v2).
Wyniki sprawdzenia pliku: `verify_file.json` (brak błędów dekodowania, przesunięcie dźwięku 0 próbek w 8 miejscach).

Co zostało poprawione w v2 (szczegóły w `report.md`, sekcja „Historia poprawek”):
- napis wtrącenia chóru „(Wywalili na bruk!)” w 99,6–102,9 s był pusty (tekst w nawiasie był wycinany w całości);
- usta chóru w tym wersie otwierały się 8 razy na 6 sylab (surowe zdarzenia stemu chórków zamiast wyrównanych sylab);
- usta liczone na siatce klatek: każda sylaba ma ≥1 klatkę otwarcia, między sylabami ≥1 klatkę zamknięcia (w v1 krótkie sylaby potrafiły zlać się w jedno otwarcie);
- scena „A pod spodem cisza” przebudowana: w v1 (klatka 71,5 s) widać było tylko czarne, nieczytelne sylwetki rąk na tle sklejki, bez lalek; w v2 nad krawędzią widać plecy lalek w ciepłym świetle show, pod nią lalkarzy w czerni;
- w repryzie postacie wynurzały się ułamek sekundy przed cięciem — teraz dopiero po cięciu;
- napis „Puste zasięgi” na przodzie sceny przesunięty niżej (zasłaniał dłonie lalek);
- wyciemnienie przed napisami końcowymi, spokojniejsze ziarno (zmiana co 2 klatki, mniejsza siła), kodowanie dwuprzebiegowe do limitu 100 MB.
