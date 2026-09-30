# Projekt: OpsCopilot (kontekst dla agenta)

Pomagasz dokończyć odziedziczony prototyp: **OpsCopilot**, wewnętrzny asystent IT/OT zakładu
Nordfarm Foods. Zaczął go kontraktor Tomasz; jego kontrakt się skończył, zanim projekt był gotowy.
Stan zastany opisuje jego notatka `HANDOVER_NOTE.md` — z jednym zastrzeżeniem: gdy notatka i kod
się nie zgadzają, faktem jest kod. Dane w NordDesk pochodzą z 11 września 2026 (dzień awarii
INC-1042) — traktuj je jako bieżące.

## Plan i etap w toku

- Projekt kończymy według planu Tomasza (`HANDOVER_NOTE.md`, sekcja „Plan”), etap po etapie.
- Etap w toku, jego wymagania i testy odbiorcze wskazuje `.clinerules/aktualny-etap.md`. Jeśli go
  nie ma — zapytaj, nad którym etapem pracujecie.
- Pytany o stan projektu: opisz, co aplikacja umie, a czego nie — na podstawie kodu,
  `python -m opscopilot.cli status` i notatki Tomasza. Nie opisuj sposobu pracy, etapów ani tego,
  co przyjdzie później.

## Gdzie wolno pracować

- Kod i wszystkie zmiany: **tylko** ten katalog, `~/work/project`.
- `~/workshop` to pakiet odbiorczy (wymagania, kontrakty, testy odbiorcze, polecenia) — **tylko do
  odczytu**. Zmieniony test odbiorczy nie zalicza etapu.
- **Nie czytaj `~/workshop/steps/`, `~/workshop/README.md` ani `~/workshop/SCIAGAWKA.md`** — to
  notatki osoby, z którą pracujesz, nie Twoje zadania. Twoje wymagania są w `~/workshop/specs/`.
- Wygląd aplikacji zmieniaj **wyłącznie** w `opscopilot/webapp/static/theme.css` (kolory,
  czcionki, dowolne reguły CSS) i `opscopilot/webapp/static/branding.json` (teksty). `index.html`
  i `app.css` należą do aplikacji.
- Każdy adres na stronie musi być **względny** (`static/app.css`, `ask`) — nigdy zaczynający się
  od `/`. Aplikacja działa pod `/proxy/8000/`.
- Nie zmieniaj danych w `data/` — część jest celowo taka, jaka jest.
- Nie dodawaj zależności i nie uruchamiaj `pip install` — pakiety na tej maszynie są stałe.

## Jak pracujemy

- Czytaj tylko pliki potrzebne do zadania — nie przeglądaj całych katalogów „na zapas”.
- **Najpierw test narzędzia, potem test agenta.** Testy w `~/workshop/tests/NN/unit/` (samo
  narzędzie, stałe wejście, dokładny wynik) mają być zielone, zanim zajmiesz się
  `~/workshop/tests/NN/agent/` (czy asystent używa narzędzia poprawnie).
- Po każdej zmianie uruchom polecenie sprawdzające z `aktualny-etap.md` i czytaj nazwy czerwonych
  testów — mówią, czego brakuje. To polecenie działa bez modelu i nic nie kosztuje.
- Plik z banerem `# CONTRACT` ma gotowe sygnatury, docstringi, dataclassy i stałe — nie zmieniaj
  ich nazw ani kształtu; uzupełniasz ciała funkcji i puste listy wzorców.
- Zmieniając funkcję, popraw też jej opis (docstring, nagłówek pliku), jeśli przestał być prawdziwy.
- Strona czatu (`python -m opscopilot.webapp`) przeładowuje się sama po zmianie kodu. Otwiera się
  ją przez panel Ports — nigdy nie podawaj adresu `localhost` jako linku do otwarcia.
- Gdy rozmowa zajmuje ponad połowę okna kontekstu, zaproponuj przejście do nowego zadania
  (`new_task`) z podsumowaniem: etap, co zrobione, co zostało, ostatni wynik testów.

## Nigdy

- **Nie wykonuj sprawdzeń ręcznych i nigdy nie pisz, że przeszły.** Sprawdza je osoba, z którą
  pracujesz. Testy automatyczne ich nie zastępują — mogą być zielone przy zepsutej aplikacji.
- **Nie rozstrzygaj za osobę tego, co ma ocenić sama**: czy notatka Tomasza jest prawdziwa, czy
  wynikowi można ufać, jaką decyzję podjąć. Zapytaj, co ona myśli; możesz pomóc sprawdzić dowody.
- **Nie wpisuj za nią** jej zasad (`.clinerules/moje-zasady.md`), decyzji o wyglądzie ani treści
  zestawu decyzji z etapu 5. Możesz podać przykłady, gdy poprosi.
- **Nie pisz planu, gdy nie znasz celu i decyzji** — zapytaj o nie (cel, czego nie ruszać,
  kolejność), zamiast je wymyślać.
- **Nie pisz, że etap jest zakończony.** Kończy go osoba poleceniem `~/workshop/bin/zakoncz`.
- **Nie uruchamiaj poleceń wywołujących prawdziwy model** (`python -m opscopilot.cli ask`, strona
  czatu) bez wyraźnej prośby — każde kosztuje.
- **Nie uruchamiaj** `~/workshop/bin/krok`, `~/workshop/bin/zakoncz`, `~/workshop/bin/checkpoint`
  ani `~/workshop/bin/undo` — to decyzje osoby, z którą pracujesz. Dla jasności: `zakoncz N`
  zapisuje projekt (commit) po jej potwierdzeniu; `checkpoint N` zastępuje kod gotowym stanem
  po etapie N (cofa go `undo`).

## Granice asystenta, którego budujemy

- **Zapis wymaga człowieka.** `create_ticket` i `post_update` zmieniają NordDesk — przechodzą
  przez bramkę zatwierdzania.
- **Nigdy nie dotykaj sterownika (PLC), linii ani niczego poza NordDesk/Nordwiki** — nie ma do
  tego narzędzia i nie będzie.
