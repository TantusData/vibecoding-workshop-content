# Etap 8 z planu Tomasza — Szlify: ślad, koszty, model wpływu, raport zmiany

## Decyzje

- **Ślad każdej odpowiedzi** pochodzi z dziennika audytu, nie z relacji modelu — widać go na
  stronie (prawy panel) i w terminalu (`ask --trace`).
- **Koszt każdego etapu** jest zapisywany (tokeny, kwota z bramki) — `usage`.
- **Model ML Tomasza staje się narzędziem** asystenta (`impact_estimate`): pytanie „jak
  poważne jest INC-1042?" kończy się liczbami z modelu, nie z modelu językowego.
- **Raport zmiany** w formacie Marka: dane zbierają narzędzia, model tylko pisze tekst według
  szablonu, a aplikacja sprawdza obowiązkowe nagłówki.

## Czego nie robimy

- Nie budujemy tych dodatków — oglądamy i oceniamy całość.

## Etap 8 — kontrakt: szlify (gotowe, do obejrzenia)

Ten etap przychodzi gotowy (właściciel projektu pobiera go sam); jego wygląd, zasady i zestaw
decyzji zostają bez zmian. Ponad etap 7 dochodzi:

- **Ślad:** `ask_traced()` zwraca zdarzenia audytu tej tury; strona czatu rysuje je w prawym
  panelu; `python -m opscopilot.cli ask --trace "…"` wypisuje je z sumami.
- **Zużycie:** każde wywołanie modelu zapisuje wiersz (etap, tokeny, koszt z bramki);
  `python -m opscopilot.cli usage` sumuje je per etap.
- **Model wpływu jako narzędzie:** `impact_estimate` jest narzędziem pętli — „jak poważne jest
  INC-1042?" pobiera zgłoszenie, uruchamia model wpływu Tomasza i odpowiada liczbami.
- **Raport zmiany:** `python -m opscopilot.cli report --shift day|night` — podsumowanie zmiany
  w formacie Marka (`opscopilot/templates/handover.md`) z żywych zgłoszeń i procedur,
  sprawdzone pod kątem obowiązkowych nagłówków (jedna poprawka).
- **Pokaz:** `python scripts/demo.py` — cały dzień w jednym przebiegu (prawdziwy model).

Testy: `~/workshop/tests/08/`.

## Ślad i koszt — gdy właściciel projektu buduje je sam (przed pobraniem gotowej wersji)

Właściciel projektu może zaplanować tę część z Tobą; o tym, co pokazać w terminalu, decyduje on.
Gotowe od etapu 6: `govern/audit.py` — `with audit.turn() as (turn_id, events):` nadaje każdemu
zdarzeniu z tej tury `turn_id` i `ms` i zbiera je w `events`; `store.add_usage(session_id, step=…,
provider=…, model=…, input_tokens=…, output_tokens=…, cost_usd=…, tool=…)` i `store.usage_rows()`.
Strona czatu (`webapp/app.py`, `index.html`) już przyjmuje `trace` z `ask_traced()` i rysuje go
w prawym panelu — nie zmieniaj ich.

- `ask_traced(question, session_id)` wykonuje turę wewnątrz `audit.turn()` i zwraca
  `(answer, turn_id, events)` — zdarzenia tej tury, po kolei.
- Każde wywołanie modelu zapisuje wiersz zużycia (`store.add_usage`) z etapem (`route`,
  `answer_tickets`, `answer_docs`, …), tokenami i kosztem z bramki.
- `ask --trace` wypisuje odpowiedź, a pod nią ślad w formie, którą wybierze właściciel projektu.
  Opcjonalnie `usage` — koszty zsumowane według etapu.

## Sprawdzanie

Po każdej zmianie: `~/workshop/bin/sprawdz 8`. Etap kończy właściciel projektu — po swoich sprawdzeniach ręcznych.
