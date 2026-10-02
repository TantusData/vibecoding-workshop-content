# Etap 3 z planu Tomasza — Pamięć rozmowy

## Decyzje

- Pamiętamy **ostatnie 20 wiadomości** rozmowy, w limicie ok. **6000 tokenów**; gdy się nie
  mieści, odpadają najstarsze całe wiadomości.
- Pamięć jest **per rozmowa** (sesja): `--session <nazwa>`; bez tej opcji — bieżąca rozmowa.
- Magazyn (SQLite) jest gotowy; piszemy logikę okna rozmowy.
- Stare wyniki narzędzi wracają do rozmowy w jednym z trzech trybów: `replay` (w całości,
  domyślnie), `drop` (bez nich), `summarise` (jednolinijkowy ślad).
- Rozmowę widzi **i** planista (co sprawdzić), **i** wywołanie odpowiedzi.
- Odmowa też jest częścią rozmowy (przyda się w etapie 6).

## Czego nie robimy

- Pamięci długoterminowej (faktów między rozmowami).
- Streszczania rozmowy modelem (dla chętnych).
- Gotowego frameworka pamięci.

## Etap 3 — kontrakt: pamięć rozmowy

**Cel:** „A kto nad nim pracuje?" (bez numeru zgłoszenia) działa w tej samej rozmowie.

**Testy:** `~/workshop/tests/03/unit/test_history.py`, potem
`~/workshop/tests/03/agent/test_ask_with_history.py`.

## Kontrakt

- `opscopilot/store.py` jest gotowy (SQLite, tabela `messages`).
- `opscopilot/history.py`:
  - `record_turn()` — zapisuje pytanie, wywołania narzędzi z wynikami i odpowiedź, w kolejności;
  - `window()` — ostatnie `OPSCOPILOT_HISTORY_MESSAGES` (20) wiadomości użytkownik/asystent,
    w limicie `OPSCOPILOT_HISTORY_TOKENS` (6000, szacunek), najstarsze całe wiadomości odpadają
    pierwsze, okno zaczyna się od wiadomości użytkownika;
  - `_fold()` — wiersze narzędzi wkładane do tury asystenta wg `OPSCOPILOT_HISTORY_TOOL_RESULTS`
    = `replay` | `drop` | `summarise`.
  - Dokładne formaty zapisu (`<tool_result tool=… args=…>`, `(looked up … at …)`) są przypięte
    w testach jednostkowych — testy są tu specyfikacją.
  - `last_tool_call()` — **w tej części etapu zostaje zaślepką**.
- `opscopilot/cli.py`: identyfikator sesji (`--session`, `OPSCOPILOT_SESSION`,
  `var/current_session`, polecenia `history new` / `history show`). Opcja `ask --session <nazwa>`
  już jest (Tomasz), ale dotąd nic nie zapamiętuje; `history show --session <nazwa>` pokazuje
  tury tej rozmowy; `ask --new "…"` zaczyna nową rozmowę (staje się bieżącą) i zadaje w niej
  pytanie — tych trzech używa właściciel projektu w swoich sprawdzeniach. Wcześniejsze tury trafiają
  **i** do planisty, **i** do wywołania odpowiedzi; `llm/prompts/answer_history.md` odpowiada na
  turę, która niczego nie sprawdza, **gdy rozmowa ma wcześniejsze tury**. Bez wcześniejszych tur
  (np. `ask()` bez `session_id`) taka tura nadal idzie do `chat.md`, jak w etapie 2.
- Formy przypięte w testach CLI: ścieżka pliku bieżącej rozmowy to stała modułu
  `SESSION_FILE` w `cli.py`, czytana w chwili wywołania (testy ją podmieniają — nie jako domyślny
  argument funkcji); `history new` wypisuje **samo** id nowej rozmowy; `history show` zaczyna od
  linii `session <id>`, potem jedna linia na wiadomość (rola i treść). Rozmowa trafia do planisty
  i do odpowiedzi jako wcześniejsze **wiadomości** (lista `messages`), nie wklejona w tekst.
- **Kto ustala rozmowę.** `ask(question, session_id=None)` / `ask_traced(question, session_id=None)`
  pamiętają tylko przy **podanym** `session_id`: bez niego — bez historii i bez zapisu (tak woła
  je np. kod, który nie prowadzi rozmowy). Kolejność `--session` → `OPSCOPILOT_SESSION` →
  `var/current_session` rozstrzyga **wyłącznie polecenie `ask` w CLI** i przekazuje wynik jako
  `session_id`; strona czatu przekazuje własny identyfikator.
- Odmowy to też tury (ważne od etapu 6): odrzucona wiadomość i stałe zdanie odmowy są zapisane
  jak każda inna wymiana, bez wierszy narzędzi. Nie budować wyjątku.
- `is_state_question()` jest gotowe (rozpoznaje pytania o stan, także po polsku).

## Sprawdzanie

Po każdej zmianie: `~/workshop/bin/sprawdz 3a`. Etap kończy właściciel projektu — po swoich sprawdzeniach ręcznych.
