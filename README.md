# Warsztat: OpsCopilot — dokończ projekt po poprzedniku

**Historia.** Nordfarm Foods to zakład spożywczy z sześcioosobowym zespołem IT/OT, który na
zmiany utrzymuje linie pakowania, MES, paletyzatory, drukarki i VPN. Przy każdym przekazaniu
zmiany coś ginie: stan awarii ukryty w komentarzu, pytanie o VPN zadawane po raz setny, hasło
wklejone do zgłoszenia, raport zmiany pisany ręcznie. Kontraktor Tomasz zaczął budować
**OpsCopilot** — asystenta, który ma w tym pomóc — i odszedł, zostawiając notatkę. Przez osiem
kroków dokończysz go z agentem programistycznym (**Cline**, panel po lewej): Ty dajesz kontekst,
decyzje i sprawdzasz wynik, agent pisze kod.

## Jak zacząć

```bash
~/workshop/bin/krok 1
```

To polecenie zaczyna krok: pobiera jego opis, wymagania i testy, mówi agentowi, który etap planu
jest w toku, i pokazuje, od czego zacząć. Opis kroku otwiera się w `~/workshop/steps/NN/README.md`.

**Dwa rodzaje materiału.** Opis kroku (`steps/`) jest **dla Ciebie**: zadania, odkrycia,
sprawdzenia ręczne, podpowiedzi. Agent go nie czyta — dostaje tylko wymagania i kontrakt
(`specs/`) oraz testy (`tests/`). Dla agenta kroki to **etapy planu Tomasza** z jego notatki
(krok N = etap N); o kursie agent nic nie wie.

**Każdy krok (i każda część A/B) w nowym zadaniu Cline** (przycisk **+**). Krótsza rozmowa to
lepsze odpowiedzi i niższy koszt.

## Mapa kroków

| Krok | Co dodaje (dla zakładu) |
|---|---|
| 01 | Wiesz, co naprawdę jest w projekcie; agent zna zasady projektu; aplikacja ma Twój wygląd |
| 02 | Asystent czyta system zgłoszeń; zapis tylko za zgodą człowieka |
| 03 | Asystent pamięta rozmowę (część A) — i nie wierzy pamięci bardziej niż systemowi (część B) |
| 04 | Asystent używa kilku narzędzi do jednego pytania, z limitem |
| 05 | Zespół decyduje, czego asystent ma odmawiać |
| 06 | Asystent odmawia tego, czego nie powinien, nie zdradza haseł i zostawia ślad |
| 07 | Asystent odpowiada z dokumentacji ze źródłem (część A) — i znajduje właściwy fragment (część B) |
| 08 | Gotowa całość: ślad, koszty, model ML jako narzędzie, raport zmiany |

## Jak wygląda każdy krok

1. **Gdzie jestem** — po co ten krok zakładowi (początek opisu kroku; wypisuje go też `bin/krok`).
2. **Pierwsza czynność** — jedna rzecz do zrobienia od razu, zwykle mały eksperyment.
3. **Wymagania i decyzje** — co ustaliliśmy i czego *nie* robimy (te same trafiają do agenta, w `specs/`).
4. **Polecenie planu** — piszesz je samodzielnie, w trybie **Plan**, według szkieletu niżej; czytasz plan, poprawiasz, potem **Act**.
5. **Jak sprawdzić** — automatycznie: agent uruchamia `~/workshop/bin/sprawdz N`
   (bez modelu, bez kosztu); ręcznie: lista poleceń z oczekiwanym wynikiem, wykonujesz Ty.
6. **Kiedy koniec** — `~/workshop/bin/zakoncz N`: sprawdza testy, przeprowadza Cię przez
   sprawdzenia ręczne jedno po drugim (o każde pyta), zapisuje projekt. Po tym poleceniu krok
   jest zrobiony. Zielone testy to za mało — sprawdzenia ręczne wyłapują to, czego testy nie widzą.

## Szkielet polecenia planu

- **Cel** — jednym zdaniem, po swojemu: co ma umieć asystent po tym kroku.
- **Gdzie są wymagania** — `~/workshop/specs/NN/spec.md` (wymagania, decyzje i kontrakt dla
  agenta; opisu kroku agentowi nie podawaj).
- **Czego nie ruszać** — `~/workshop`, nazwy oznaczone `CONTRACT`, dane w `data/`.
- **Kolejność** — najpierw testy narzędzia (`tests/NN/unit/`), potem testy asystenta
  (`tests/NN/agent/`).
- **Jak sprawdzić** — `~/workshop/bin/sprawdz N` po każdej zmianie.
- **Czego oczekuję w planie** — lista plików do zmiany i po co; pytania, jeśli coś jest niejasne.

## Polecenia

Wszystkie polecenia terminala w jednym miejscu, także na wypadek problemów: `SCIAGAWKA.md`.

| Polecenie | Kiedy |
|---|---|
| `~/workshop/bin/krok N` | początek kroku (kroki 3 i 7 mają część B: `3b`, `7b`) |
| `~/workshop/bin/sprawdz N` | czy testy przechodzą (uruchamia je agent) |
| `~/workshop/bin/zakoncz N` | koniec kroku (uruchamiasz Ty) |
| `~/workshop/bin/checkpoint N` | utknięcie: gotowy stan projektu po kroku N (najpierw zapisuje Twój) |
| `~/workshop/bin/undo` | cofa ostatni checkpoint |

## Dwa katalogi

| | Co to | Czy zmieniasz? |
|---|---|---|
| `~/work/project` (**Projekt**) | **Twój** projekt. Tu pracuje agent. | Tak — tylko tutaj. |
| `~/workshop` (**Materiały**) | Kurs: opisy kroków (dla Ciebie), wymagania i testy (dla agenta), polecenia. | **Nigdy.** |

## Zasady, które chronią Twoją pracę

- **Gdy Cline pracuje, zostań na tej stronie.** Jeśli połączenie padnie: odśwież stronę (F5),
  otwórz panel Cline i kliknij **Resume Task** — rozmowa i zadanie wracają.
- **Aplikację otwieraj przez panel Ports**, nigdy pod adresem `localhost`.
- **Twój wygląd aplikacji, Twoje zasady dla agenta i Twój zestaw testowy** są chronione przed
  checkpointem (lista: `keep.txt`).
- Nie instaluj pakietów (`pip install`) — wszystko, czego potrzeba, już jest.
