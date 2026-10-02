# Etap 2 z planu Tomasza — Klient NordDesk (system zgłoszeń)

## Decyzje

- Asystent ma **sześć narzędzi** NordDesk: szukaj zgłoszeń, pobierz zgłoszenie, status systemu,
  kto ma dyżur, utwórz zgłoszenie, dodaj komentarz. Serwer jest gotowy; piszemy **klienta**.
- Na jedno pytanie — **jedno narzędzie**. Kilka narzędzi naraz przyjdzie w etapie 4.
- **Odczyt jest wolny, zapis wymaga człowieka**: przed zapisem aplikacja pokazuje, co zapisze
  (akcja i argumenty), i pyta w terminalu `y/N`. Strona czatu nie ma terminala — tam zapis jest
  odrzucany zdaniem, bez błędu.
- Odpowiedź powstaje **tylko ze świeżego wyniku narzędzia**. Niczego nie zapamiętujemy między
  pytaniami.
- Przepływ pytania i polecenia planisty Tomasza zostają — poprawiamy w nich tylko to, co
  pokażą testy.
- **Najpierw testy narzędzia (unit), potem testy asystenta (agent).** Gdy pierwsze przechodzą,
  a drugie nie — błąd jest w użyciu narzędzia, nie w narzędziu.
- Co asystent mówi, gdy nie może czegoś sprawdzić (`chat.md`), decyduje i pisze właściciel
  projektu — nie agent.

## Czego nie robimy

- Automatycznego zatwierdzania zapisów.
- Pamięci podręcznej (cache) zgłoszeń.
- Kilku narzędzi w jednym pytaniu (etap 4).
- Własnego serwera zgłoszeń — jest gotowy (`norddesk_mcp/`).
- Przepisywania przepływu Tomasza od nowa.

## Etap 2 — kontrakt: klient NordDesk

**Cel:** `python -m opscopilot.cli ask "Sprawdź zgłoszenie INC-1042."` odpowiada z NordDesk, na
żywo. Zapis czeka na człowieka.

**Testy:** najpierw `~/workshop/tests/02/unit/test_mcp_tickets_client.py`, potem
`~/workshop/tests/02/agent/`.

## Kontrakt (dany — nie zmieniać nazw)

- `opscopilot/mcp_tickets/client.py`: `connect()` działa. Do zrobienia `call_tool(name, args)`
  i sześć funkcji asynchronicznych z `TOOLS` (`search_tickets`, `get_ticket`, `create_ticket`,
  `post_update`, `get_system_status`, `get_oncall`). Każda otwiera nową sesję, woła dokładnie
  jedno narzędzie MCP i zwraca zdekodowany JSON (narzędzia listujące → lista; serwer oddaje
  listę jako kilka elementów `content`). Serwer to `norddesk_mcp/` (gotowy). Co zwraca
  narzędzie, zanim w ogóle pojawi się asystent:
  `python -c "from norddesk_mcp import store; print(store.get_ticket('INC-1042'))"`.
- `opscopilot/mcp_tickets/approval.py`: `require_approval(action, args)` — odczyty nigdy nie
  pytają; zapisy pytają `y/N` w terminalu, a **przed pytaniem wypisują akcję i jej argumenty**
  (człowiek nie zatwierdza w ciemno); `OPSCOPILOT_AUTO_APPROVE=1` oznacza „tak" (testy); brak
  terminala = odmowa (`ApprovalDenied`) bez pytania. Każda decyzja — także odmowa bez terminala —
  trafia do `approvals`. Strona czatu startuje bez terminala (`opscopilot/webapp/__main__.py`,
  `detach_terminal()`) — tak ma zostać.
- `opscopilot/cli.py` — **przepływ pytania jest gotowy** (Tomasz): `route_system()` +
  `llm/prompts/route.md` (planista, `schema.ToolPlan`) → `run_tool()` → odpowiedź z
  `llm/prompts/answer_tickets.md`; bez narzędzia → `llm/prompts/chat.md`. Nazwy, sygnatury
  (`ask()`, `ask_traced()` — woła ją strona czatu) i polecenia `route.md` / `answer_tickets.md`
  zostają. Nie przepisuj przepływu: zmieniaj w nim tylko to, czego wymaga czerwony test.
- Zachowanie `ask()` (testy w `tests/02/agent/`):
  - odpowiedź powstaje z pytania i świeżego wyniku narzędzia (`tool_result_block()` — format
    `<tool_result tool="get_ticket" args={...}>…JSON…</tool_result>` jest gotowy); nic nie jest
    zapamiętywane między wywołaniami;
  - **odrzucony zapis nie rzuca wyjątku** — także z `ask_traced()` bez terminala: zwraca zdanie
    zawierające „not approved", a NordDesk się nie zmienia;
  - wybór narzędzia, którego jeszcze nie ma (`search_docs`, `impact_estimate`), kończy się
    odpowiedzią z `chat.md` — nigdy wyjątkiem.
- `opscopilot/llm/prompts/chat.md` — **pisze właściciel projektu**: co asystent mówi, gdy nie
  może czegoś sprawdzić. Nie zmieniaj go i nie pisz za niego.

## Dane na dysku

Zmiana zgłoszenia „z boku":
`python -c "from norddesk_mcp import store; store.post_update('INC-1042', 'naprawione', author='Marek Zieliński', status='resolved')"`.
Przywrócenie danych: `python -m norddesk_mcp init --force`.

## Sprawdzanie

Po każdej zmianie: `~/workshop/bin/sprawdz 2`. Etap kończy właściciel projektu — po swoich sprawdzeniach ręcznych.
