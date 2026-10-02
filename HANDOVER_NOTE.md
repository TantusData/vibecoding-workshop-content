# Przekazanie — prototyp OpsCopilot

Cześć, tu Tomasz — kontraktor, od którego to wszystko się zaczęło. Kontrakt skończył się, zanim
projekt był gotowy; przepraszam za przekazanie czegoś w połowie. Oto stan rzeczy.

## Co działa już teraz

- Połączenie z modelem (`opscopilot/llm/client.py`) — przez bramkę LiteLLM firmy, model
  `bedrock-claude`, klucz z zmiennej środowiskowej `LITELLM_VIRTUAL_KEY` (na naszych maszynach już
  ustawiony). Ustrukturyzowane odpowiedzi (JSON wg schematu) są zrobione i przetestowane. Ta
  część jest solidna — budujcie na niej, nie przepisujcie jej. `LLM_PROVIDER=fake` daje
  deterministyczny zamiennik do testów.
- `python -m opscopilot.cli ask "..."` — przepływ pytania jest gotowy (`opscopilot/cli.py`):
  planista (`llm/prompts/route.md`) wybiera jedno narzędzie NordDesk, aplikacja je wywołuje,
  a odpowiedź powstaje z wyniku (`answer_tickets.md`). Pytanie, które nie potrzebuje narzędzia,
  dostaje krótką odpowiedź z `chat.md` — to mój szkic na szybko. Brakuje klienta NordDesk (niżej),
  więc o zgłoszenie odpowie, że NordDesk nie jest jeszcze podłączony. Dokumentacji nie przeszukuje:
  zapytany, jakiego adresu VPN używać albo jak zrestartować MES linii pakowania — z pełnym
  przekonaniem coś wymyśli. Opcja `ask --session <nazwa>` już jest (strona czatu też wysyła
  identyfikator rozmowy), ale niczego nie zapamiętuje — pamięć to punkt 3 planu.
- Prosta strona czatu (`opscopilot/webapp/`, `python -m opscopilot.webapp`), która woła to samo
  `ask_traced()`. Brzydka, ale działa. Nie ma terminala, więc nikt przy niej nie zatwierdzi
  zapisu. `python -m opscopilot.cli status` mówi, co naprawdę działa —
  prosto z kodu.
- Oba udawane systemy: `norddesk_mcp/` (zgłoszenia, plik JSON) i `nordwiki_mcp/` (dokumentacja,
  katalog plików markdown w `data/wiki/`) to działające serwery MCP. Czytają swoje pliki przy
  każdym wywołaniu, więc dane można zmieniać w trakcie pracy. Dane w NordDesk są z dnia awarii
  paletyzatora (INC-1042, 11 września 2026) — tak zostawiłem, żeby było na czym pracować.
- Rzeczy, których nie trzeba pisać: modele danych (`schema.py`), magazyn SQLite (`store.py`),
  obsługa embeddingów (`rag/embed.py` — też przez bramkę, model `titan-embed`), klient MCP do
  wiki (`mcp_wiki/client.py`).
- Mój poboczny projekt, `opscopilot/impact/` — szacowanie przestoju i kosztu w EUR: regresor
  scikit-learn uczony na historii incydentów z `data/incidents/` (model trenuje się sam przy
  pierwszym użyciu, około sekundy). `python -m opscopilot.cli impact INC-1042` pokazuje wynik
  i czynniki, które go przesunęły; `python scripts/train_impact.py --variant leaked --eval`
  pokazuje, co złe dane robią z R². Bez żadnego LLM. Uwaga: to polecenie czyta
  `var/norddesk.json` bezpośrednio, a nie przez klienta MCP (którego nie ma) — dobre na projekt
  poboczny, nie do aplikacji.

## Co zacząłem i nie skończyłem

- `opscopilot/mcp_tickets/` — klient MCP do NordDesk. Połączenie i sygnatury funkcji są, ale
  każda funkcja to `NotImplementedError("TODO")`. To pierwsza rzecz do zrobienia — bez niej nic
  innego nie ma sensu. Do wywołań HTTP użyty jest `httpx`. Obok bramka zatwierdzania zapisów
  (`approval.py`) — też tylko sygnatura: zapis w NordDesk ma czekać na „tak" człowieka.
- `opscopilot/history.py` — pamięć rozmowy. Magazyn jest, logika okna rozmowy nie.
- `opscopilot/loop.py` — wiele narzędzi w jednym pytaniu. Same sygnatury.

## Do czego nie doszedłem

- `opscopilot/govern/` — puste funkcje. To martwi mnie najbardziej: zanim ktokolwiek spoza IT
  tego dotknie, asystent musi odmawiać tego, na co nie powinien odpowiadać, i nie dać się namówić
  na wyciek danych.
- `opscopilot/rag/` — wyszukiwanie w wiki. Embeddingi, indeks (`index.py`) i `retrieve()`
  są; brakuje dzielenia stron na fragmenty (`chunk.py`) — bez niego indeks nie ma czego
  zbudować — i podłączenia wyszukiwania do asystenta.
- Marek (kierownik zmiany) chce automatycznego podsumowania na koniec zmiany w konkretnym
  formacie. Jego szablon jest w `opscopilot/templates/handover.md`; implementacji zero.

## Plan — gdybym zostawał (albo dla tego, kto to przejmie)

1. Przejęcie: przeczytać tę notatkę i sprawdzić ją z kodem, ustawić swojego asystenta kodu
   (Cline) pod siebie w `.clinerules/moje-zasady.md`, nadać stronie czatu wygląd Nordfarm
2. Klient MCP do zgłoszeń i bramka zapisu (bez tego nic nie działa; reszta przepływu już jest)
3. Pamięć rozmowy (i zobaczyć, co psuje)
4. Pętla narzędzi
5. Ustalić, czego asystent ma odmawiać — zanim powstanie jakakolwiek blokada
6. Zabezpieczenia (guardrails)
7. Wyszukiwanie w wiki (RAG)
8. Szlify — ślad odpowiedzi i koszty, raport Marka, szacowanie wpływu jako narzędzie asystenta

Powodzenia. — T.
