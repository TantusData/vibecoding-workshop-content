# Ściągawka — polecenia w terminalu

Wszystkie polecenia wpisuje się w terminalu code-servera (menu → Terminal → New Terminal).
Nowy terminal startuje w `~/work/project`. Polecenia `python -m opscopilot…` działają tylko
w tym katalogu — w razie wątpliwości najpierw: `cd ~/work/project`.

## Kroki kursu

| Chcę… | Polecenie |
|---|---|
| zacząć krok N | `~/workshop/bin/krok N` (części B: `krok 3b`, `krok 7b`) |
| sprawdzić, czy testy przechodzą | `~/workshop/bin/sprawdz N` (części: `3a`, `3b`, `7a`, `7b`) |
| zakończyć krok (sprawdzenia ręczne + zapis) | `~/workshop/bin/zakoncz N` — na każde pytanie `t` albo `n` |
| nadrobić krok — gotowy stan po kroku N | `~/workshop/bin/checkpoint N` — potwierdź, wpisując `TAK` |
| cofnąć ostatni checkpoint | `~/workshop/bin/undo` — potwierdź, wpisując `TAK` |
| przywrócić materiały kursu, gdy `sprawdz` mówi „STOP" | `~/workshop/bin/sprawdz przywroc` |

Samo polecenie bez numeru (np. `~/workshop/bin/krok`) wypisuje, jak go użyć.

## Aplikacja

| Chcę… | Polecenie | Od kroku |
|---|---|---|
| co aplikacja naprawdę umie | `python -m opscopilot.cli status` | 01 |
| zadać pytanie | `python -m opscopilot.cli ask "Sprawdź zgłoszenie INC-1042."` | 01 |
| uruchomić stronę czatu | `python -m opscopilot.webapp`, potem panel **Ports** → port 8000 | 01 |
| zatrzymać stronę czatu | `Ctrl+C` w jej terminalu | 01 |
| szacunek przestoju i kosztu (model ML Tomasza) | `python -m opscopilot.cli impact INC-1042` | 01 |
| przywrócić dane NordDesk do stanu wyjściowego | `python -m norddesk_mcp init --force` | 01 |
| pytać w jednej, nazwanej rozmowie | `python -m opscopilot.cli ask --session demo "…"` | 03 |
| zacząć nową rozmowę | `python -m opscopilot.cli ask --new "…"` albo `python -m opscopilot.cli history new` | 03 |
| zobaczyć, co asystent pamięta | `python -m opscopilot.cli history show --session demo` | 03 |
| zobaczyć ślad odpowiedzi (narzędzia, koszt) | `python -m opscopilot.cli ask --trace "…"` | 08 |
| koszty wywołań modelu | `python -m opscopilot.cli usage` | 08 |
| raport na koniec zmiany | `python -m opscopilot.cli report --shift day` | 08 |

Pytania do aplikacji (`ask`, strona czatu) kosztują — każde to wywołanie modelu. Polecenia
`~/workshop/bin/…` są darmowe: działają bez modelu.

## Czy moja praca jest zapisana?

| Chcę… | Polecenie |
|---|---|
| ostatnie zapisy projektu | `git -C ~/work/project log --oneline -5` |
| co zmieniło się od ostatniego zapisu | `git -C ~/work/project status` |
| które kroki są zakończone | `cat ~/work/project/.git/workshop-done` |
| zapasowe gałęzie po `undo` | `git -C ~/work/project branch` (nazwy `zapas/…`) |

Projekt zapisuje się sam przy `zakoncz` i przed każdym `checkpoint`. Restart maszyny niczego
w `~/work/project` nie kasuje.

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| „Python na tej maszynie jeszcze się instaluje" | Poczekać minutę po starcie maszyny. Gotowe, gdy `ls /opt/venv/.ready` nie zgłasza błędu. |
| Połączenie padło, gdy Cline pracował | Odświeżyć stronę (F5) → panel Cline → **Resume Task**. |
| Cline nie reaguje, panel „zawieszony" | `Ctrl+Shift+P` → **Developer: Restart Extension Host** (pliki i rozmowa zostają), potem **Resume Task**. |
| Strona czatu nie otwiera się | Czy działa `python -m opscopilot.webapp` w którymś terminalu? Adres tylko z panelu **Ports**, nigdy `localhost`. |
| „address already in use" przy starcie strony | Strona już działa w innym terminalu — tam `Ctrl+C`. Albo: `pkill -f opscopilot.webapp` i uruchomić ponownie. |
| Strona pokazuje stare odpowiedzi | `Ctrl+C` w terminalu strony, potem `python -m opscopilot.webapp`. |
| `No module named opscopilot` | Terminal jest w złym katalogu: `cd ~/work/project`. |
| `sprawdz` mówi „STOP: ktoś zmienił materiały kursu" | `~/workshop/bin/sprawdz przywroc`, potem `sprawdz` jeszcze raz. Zmieniamy tylko `~/work/project`. |
| Po `checkpoint` coś zniknęło | `~/workshop/bin/undo` — wraca stan sprzed checkpointu. |
| Dane w NordDesk pomieszane po eksperymentach | `python -m norddesk_mcp init --force` |
| Nic z tego nie pomaga | Zawołaj prowadzącego. Nie instaluj pakietów (`pip install`) i nie zmieniaj `~/workshop`. |
