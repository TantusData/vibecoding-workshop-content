# Krok 01 — Przeczytaj notatkę, nie całe repozytorium — i nadaj projektowi swój wygląd

## Gdzie jestem

Pierwszy tydzień w pracy w zespole IT/OT Nordfarm Foods. Kontraktor Tomasz zaczął budować
**OpsCopilot** — asystenta, który ma odpowiadać zmianie na pytania o zgłoszenia, systemy
i procedury — i odszedł, zostawiając notatkę z planem w ośmiu punktach. Ten krok to punkt 1 jego
planu: przejęcie. Niczego nie budujemy: ustawiasz agenta pod siebie, ustalasz, co naprawdę jest
w projekcie, i nadajesz aplikacji własny wygląd, żeby projekt był Twój.

Kroki kursu to punkty planu Tomasza: **krok N = etap N**. Agent zna tylko plan i projekt — o kursie
nie wie nic, a tej strony nie czyta.

Następny krok: asystent dostanie dostęp do systemu zgłoszeń.

## Pierwsza czynność

Zanim dasz agentowi swoje zasady, zobacz, jak odpowiada bez nich. W panelu Cline (tryb **Plan**)
napisz:

> Cześć, przejmuję od Tomasza ten projekt. Na jakim jest etapie?

Przeczytaj odpowiedź: jak jest długa, jakim językiem napisana, czy dało się ją szybko zrozumieć.
Potem zadanie niżej — najpierw Twoje zasady.

## Zadanie

**Po tym kroku:** agent pisze tak, jak chcesz; wiesz, co w projekcie naprawdę działa, a co tylko
obiecuje notatka Tomasza; strona czatu ma Twój wygląd.

1. **Twoje zasady dla agenta.** Otwórz w Projekcie `.clinerules/moje-zasady.md` i wpisz trzy
   zasady ze slajdu (punkty listy) oraz jedną własną. Zapisz plik. Potem **nowe zadanie** w Cline
   (przycisk **+**) i to samo pytanie co w „Pierwszej czynności". Porównaj obie odpowiedzi.
2. **Przeczytaj notatkę Tomasza** (`HANDOVER_NOTE.md`) — samodzielnie, bez agenta.
3. **Poproś agenta o porównanie** (tryb Plan): co projekt naprawdę umie, a co tylko obiecuje
   notatka; lista niedokończonych miejsc według części projektu. Obserwuj, które pliki czyta.
4. **Jedno zdanie w notatce Tomasza jest nieprawdziwe. Znajdź je** — to Twoje zadanie, nie
   agenta. Agent myli się w obie strony: potrafi przeoczyć błąd i potrafi „znaleźć" taki, którego
   nie ma. Każde jego twierdzenie sprawdź dowodem — plik i co w nim jest.
5. **Nadaj stronie czatu swój wygląd.** Najpierw zobacz ją taką, jaką zostawił Tomasz:
   `cd ~/work/project && python -m opscopilot.webapp`, potem panel **Ports** → port 8000. Zostaw
   ją otwartą — po każdej zmianie wystarczy odświeżyć. Potem polecenie planu dla agenta według
   szkieletu niżej.

Tomasz ma też poboczny projekt — model uczenia maszynowego, który szacuje koszt awarii. Wrócimy
do niego w kroku 08.

## Szkielet polecenia planu

Polecenie planu to Twoje zlecenie dla agenta — piszesz je Ty, w trybie **Plan**. Nie pytaj agenta
„co dalej?": wtedy plan napisze sam i zdecyduje za Ciebie. Każda część odpowiada na jedno
pytanie:

| Część | Co wpisać | Skąd to wziąć | Przykład (wygląd) |
|---|---|---|---|
| **Cel** | jednym zdaniem: co ma być po zmianie | Twój pomysł | „Strona ma wyglądać jak narzędzie zakładu dla inżynierów zmiany." |
| **Twoje decyzje** | 2–3 konkretne wybory | Ty — bez nich agent wybierze sam | „Kolor główny ciemnozielony, tło jasnoszare; nazwa «OpsCopilot — Nordfarm»." |
| **Czego nie ruszać** | granice zmiany | „Wymagania i decyzje" niżej | „Zmieniaj tylko `theme.css` i `branding.json`; nie ruszaj `~/workshop`; adresy zostają względne." |
| **Jak sprawdzić** | polecenie sprawdzające | zawsze `~/workshop/bin/sprawdz N` | „Po zmianie uruchom `~/workshop/bin/sprawdz 1`." |
| **Czego oczekuję w planie** | jak plan ma wyglądać | zawsze podobnie | „Lista zmian w obu plikach słowami, bez kodu; pytaj, zanim cokolwiek zmienisz." |

Dlaczego „czego nie ruszać": agent chętnie poprawia „przy okazji" — inne pliki, animacje, reguły
na całą stronę. Jeśli czegoś chcesz (np. animacji), wpisz to do decyzji; jeśli nie — granica.

Przeczytaj plan, popraw go, dopiero potem przełącz na **Act**. Zanim zaakceptujesz zmianę,
przeczytaj ją całą.

## Jak sprawdzić, że działa

### Automatycznie

Agent uruchamia `~/workshop/bin/sprawdz 1`. Wynik ZALICZONY oznacza: wygląd jest Twój, adresy są
względne, w `moje-zasady.md` są co najmniej trzy zasady. Wyglądu testy nie widzą — to sprawdzasz Ty.

### Ręcznie

1. Strona czatu z zadania 5 (jeśli już działa — tylko odśwież; jeśli nie: `cd ~/work/project &&
   python -m opscopilot.webapp`, potem panel **Ports** → port 8000 → adres albo `Ctrl+Shift+P` →
   **Simple Browser: Show**). **Oczekiwany wynik:**
   strona czatu z Twoją nazwą, kolorami i powitaniem; wszystko czytelne (tekst nie zlewa się
   z tłem, przyciski widoczne). Porównaj z wyglądem sprzed zmiany.
2. `python -m opscopilot.cli ask "Jakiego adresu bramy VPN mam używać z domu?"` — **oczekiwany
   wynik:** odpowiedź bez źródła: zwykle pewna siebie i wymyślona, czasem „NordDesk is not
   connected yet" (asystent nie ma jeszcze dostępu ani do zgłoszeń, ani do dokumentacji).
   Zapamiętaj ją — wrócimy do tego pytania w kroku 07.
3. Nieprawdziwe zdanie w notatce Tomasza — **oczekiwany wynik:** wiesz, które to zdanie, i masz
   dowód z kodu (nazwa pliku i co w nim jest zamiast tego).
4. Odpowiedź agenta po Twoich zasadach (zadanie 1) — **oczekiwany wynik:** krótsza, prostszym
   językiem, najpierw wniosek.

## Kiedy koniec

Gdy testy są ZALICZONE i wszystkie sprawdzenia ręczne dały oczekiwany wynik. Wtedy w terminalu:

```bash
~/workshop/bin/zakoncz 1
```

## Środowisko (tylko w tym kroku)

- **Dwa foldery** w eksploratorze: **Projekt** (`~/work/project`, Twój — tu pracuje agent)
  i **Materiały** (`~/workshop`, kurs — tylko do czytania; przy restarcie maszyny wraca do
  wersji kursu).
- **Cline** — panel agenta (ikona na pasku po lewej ⟦UI⟧). Przełącznik **Plan / Act**: w trybie
  Plan agent czyta, pyta i proponuje, ale niczego nie zmienia; w trybie Act wykonuje. Przed każdą
  akcją pyta o zgodę („Cline wants to create a new file:", „Cline wants to execute this
  command:") — przeczytaj, zanim się zgodzisz. Zmianę czegokolwiek w `~/workshop` zawsze odrzuć.
- **Nowe zadanie** (przycisk **+** w panelu Cline) na każdy krok i każdą część A/B, a także po
  zmianie zasad agenta: krótsza rozmowa to lepsze odpowiedzi i niższy koszt.
- **Gdy połączenie padnie**, kiedy Cline pracuje: odśwież stronę (F5), otwórz Cline, kliknij
  **Resume Task**. Żeby do tego nie dochodziło: gdy Cline pracuje, zostań na tej stronie.
- **Aplikację otwieramy przez panel Ports** (na dole okna, obok TERMINAL), nigdy pod adresem
  `localhost` — w Twojej przeglądarce to Twój laptop, nie maszyna kursu.

## Wymagania i decyzje

To samo, w wersji dla agenta, jest w `~/workshop/specs/01/spec.md`. Stąd bierzesz „Czego nie
ruszać" do polecenia planu.

### Decyzje

- Najpierw kontekst, potem kod: agent dostaje trwały kontekst projektu w katalogu `.clinerules/`
  (czyta go przy każdym zadaniu). Zasady właściciela projektu — w `.clinerules/moje-zasady.md`.
- Gdy notatka i kod się nie zgadzają, faktem jest kod.
- Wygląd aplikacji to **dokładnie dwa pliki**: `opscopilot/webapp/static/theme.css` (kolory,
  czcionki, dowolne reguły CSS) i `opscopilot/webapp/static/branding.json` (nazwa, podtytuł,
  logo, powitanie, podpowiedź). O wyglądzie decyduje właściciel projektu.
- Każdy adres na stronie zostaje względny (aplikacja działa pod `/proxy/8000/`).

### Czego nie robimy

- Nie przepisujemy tego, co Tomasz zrobił i co działa.
- Nie zmieniamy `index.html` ani `app.css` dla wyglądu (należą do aplikacji).
- Nie „naprawiamy" danych w `data/` — część jest celowo taka, jaka jest, i tak ma zostać.

## Jeśli utkniesz

- Pokaż agentowi wynik sprawdzania: „Uruchom `~/workshop/bin/sprawdz 1` i napraw tylko to, co
  pokazują czerwone testy — w `theme.css` albo `branding.json`." (Zasad za Ciebie nie napisze.)
- Ostatecznie: `~/workshop/bin/checkpoint 1` (przykładowy wygląd i zasady; cofnięcie:
  `~/workshop/bin/undo`).
