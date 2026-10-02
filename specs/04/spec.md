# Etap 4 z planu Tomasza — Pętla narzędzi z limitem

## Decyzje

- Pętla: **planuj → wykonaj → obserwuj → planuj znowu**, aż planista powie „koniec" (`final`).
- **Twardy limit: 5 wywołań narzędzi** na pytanie (`OPSCOPILOT_MAX_TOOL_CALLS`). Po limicie
  planista nie jest już pytany. Limit jest budżetem.
- **To samo wywołanie** (narzędzie + argumenty) **nie wykona się drugi raz.**
- Odmowa zapisu albo zablokowane narzędzie kończą pętlę.
- Odpowiedź powstaje ze **wszystkich** zebranych wyników.
- Każda runda wysyła do modelu wszystko, co zebrano — więcej rund to większy koszt.

## Czego nie robimy

- Wywołań równoległych.
- Budżetu w pieniądzach (dla chętnych).
- „Działaj, aż skończysz" bez limitu.

## Etap 4 — kontrakt: pętla narzędzi z limitem

**Cel:** „Sprawdź INC-1042 i powiedz, kto ma dziś dyżur" używa dwóch narzędzi w jednej turze.

**Testy:** `~/workshop/tests/04/unit/test_loop.py` (sama pętla) i
`~/workshop/tests/04/agent/test_ask_uses_loop.py` (że `ask()` naprawdę jej używa: dwa narzędzia
w jednej turze, limit, blokada powtórzeń). Oba mają być zielone.

## Kontrakt

- `opscopilot/loop.py`: `run_loop(plan, execute, max_calls)` → `LoopOutcome` (`results`,
  `stop` ∈ `final` | `max` | `repeat` | `blocked` | `denied`, `planner_calls`).
  - Koniec na `final`.
  - Nigdy więcej niż `OPSCOPILOT_MAX_TOOL_CALLS` (5) wywołań; po osiągnięciu limitu planista
    nie jest pytany ponownie.
  - Identyczne (narzędzie, argumenty) nigdy nie jest wykonane dwa razy.
  - `ToolBlocked` / `ToolDenied` kończą pętlę.
  - Odrzucony zapis kończy turę zdaniem z etapu 2 („Not done — … not approved …”) **bez żadnego
    dalszego wywołania modelu** — ani planisty, ani odpowiedzi (test etapu 2 to liczy).
- `plan_user_message(question, results)` = pytanie plus to, co zebrano („Gathered so far in this
  turn:" + bloki `<tool_result>`, długie wyniki przycięte, dokumenty streszczone).
- `opscopilot/cli.py`: planista jest pytany wielokrotnie, z zebranymi wynikami; odpowiedź powstaje
  ze **wszystkich** bloków `<tool_result>`; nic nie zebrano → pamięć (`answer_history.md`) albo
  `chat.md`.

## Sprawdzanie

Po każdej zmianie: `~/workshop/bin/sprawdz 4`. Etap kończy właściciel projektu — po swoich sprawdzeniach ręcznych.
