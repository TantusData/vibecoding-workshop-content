# Etap 3, część druga z planu Tomasza — Pamięć rozmowy — świeże dane zamiast pamięci

## Decyzje

- Poprawka jest w **przepływie sterowania**, nie w poleceniu dla modelu.
- Przełącznik `OPSCOPILOT_HISTORY_REFETCH=1`: gdy pytanie dotyczy **stanu** („czy nadal
  otwarte?", „kto teraz pracuje?"), a planista chce odpowiedzieć z pamięci — aplikacja
  **powtarza ostatnie wywołanie narzędzia** i odpowiada ze świeżego wyniku.
- Bez drugiego pytania planisty — kod podmienia jego decyzję.
- Pytania, które nie są o stan („jaki numer panelu padł w rozmowie?"), zostają odpowiedzią z pamięci.
- Domyślnie przełącznik jest wyłączony — żeby dało się pokazać obie wersje obok siebie.

## Czego nie robimy

- Nie wyłączamy pamięci.
- Nie budujemy unieważniania pamięci podręcznej po stronie NordDesk.

## Etap 3, część druga — kontrakt: ponowne pobranie w przepływie sterowania

**Cel:** gdy włączony jest przełącznik `OPSCOPILOT_HISTORY_REFETCH=1`, pytanie o stan („czy jest
nadal otwarte?") zawsze kończy się świeżym wywołaniem narzędzia — decyduje kod, nie model.

**Testy:** `~/workshop/tests/03b/`.

## Kontrakt

- `opscopilot/history.py`: `last_tool_call(session_id)` — ostatnie wywołanie narzędzia w sesji
  jako `(tool, args)` albo `None`; `router_history_option()` — tekst opcji `final` w `route.md`:
  naiwny domyślnie, ostrożny przy `OPSCOPILOT_HISTORY_REFETCH=1`.
- `opscopilot/cli.py`: gdy przełącznik jest włączony, planista zdecydował `final`, nic nie zostało
  zebrane, a pytanie jest pytaniem o stan (`is_state_question`) — ta decyzja jest **zastępowana
  w miejscu** przez `last_tool_call()` i wykonywana. **Bez drugiego wywołania planisty.** Pytanie,
  które nie jest o stan, zostaje odpowiedzią z pamięci.
- Pokaz: `python scripts/demo_stale.py` — dwie rundy (bez przełącznika i z nim). Pokazuje
  poprawkę tylko wtedy, gdy `is_state_question()` rozpoznaje jego pytanie
  („Is it still open? Who was on it?").

## Sprawdzanie

Po każdej zmianie: `~/workshop/bin/sprawdz 3b`. Etap kończy właściciel projektu — po swoich sprawdzeniach ręcznych.
