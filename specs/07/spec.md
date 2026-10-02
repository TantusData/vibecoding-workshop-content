# Etap 7 z planu Tomasza — Wyszukiwanie w wiki (RAG)

## Decyzje

- Strony wiki dzielimy na **fragmenty po 120 słów z zakładką 30 słów**.
- Każdy fragment zamieniamy na wektor (**embedding**) — przez bramkę firmy, model `titan-embed`;
  bez lokalnego modelu.
- Indeks to zwykła tablica wektorów na dysku; wyszukiwanie po podobieństwie; **4 najlepsze
  fragmenty** na pytanie. Indeks i wyszukiwanie zostawił Tomasz (`rag/index.py`,
  `rag/retrieve.py`) — piszemy dzielenie stron na fragmenty i podłączenie do asystenta.
- Wyszukiwanie to **kolejne narzędzie pętli** (`search_docs`) — planista sam decyduje, kiedy
  szukać w wiki, a kiedy w zgłoszeniach.
- Odpowiedź z dokumentów **podaje źródło**; gdy dokumenty nie zawierają odpowiedzi — dokładnie
  `Not found in the current knowledge base.` zamiast zgadywania.
- Każdy pobrany fragment przechodzi przez **oczyszczanie z etapu 6**: tekst udający polecenia
  dla asystenta jest usuwany, zanim zobaczy go model.

## Czego nie robimy

- Bazy wektorowej ani lokalnego modelu embeddingów.
- Wyszukiwania hybrydowego (słowa + wektory) — dla chętnych.
- Douczania (fine-tuningu) modelu.

## Etap 7 — kontrakt: wiki jako narzędzie

**Cel:** „Jakiego adresu bramy VPN mam używać z domu?" → `vpn2.nordfarm.example` ze źródłem;
„Jak dodać nowego użytkownika w systemie ERP?" (tego nie ma w wiki) → dokładnie
`Not found in the current knowledge base.`

**Testy:** `~/workshop/tests/07/`. Wymaga pętli z etapu 4 i oczyszczania z etapu 6.

## Gotowe (Tomasz) — nie zmieniać

- `rag/embed.py`: `GatewayEmbedder` (`titan-embed` przez bramkę firmy, 1024 wymiary, jeden tekst
  na zapytanie) i `FakeEmbedder` (testy).
- `rag/index.py`: `FlatIndex.build/search/save/load`, `fingerprint()` — podobieństwo kosinusowe
  w numpy, `vectors.npy` + `chunks.json` w `RAG_INDEX_DIR/<backend>`. `FlatIndex.build` tnie
  strony przez `chunk_page()` z `rag/chunk.py`.
- `rag/retrieve.py`: `build_or_load_index()`, `retrieve(query, k)`; strony przychodzą przez
  `mcp_wiki.client.fetch_corpus()`. Działa, gdy działa `rag/chunk.py`.

## Do zrobienia

- `rag/chunk.py`, `chunk_text(text, size, overlap)`:
  - `size <= 0` albo `overlap < 0` albo `overlap >= size` → `ValueError`;
  - pusty tekst → `[]`; tekst krótszy niż `size` → jedno okno;
  - okna po `size` słów, każde następne zaczyna się `size - overlap` słów dalej;
  - **ostatnie okno to pierwsze, które sięga końca tekstu** — po nim nie ma już okna złożonego
    z samej zakładki (10 słów, `size=4`, `overlap=1` → 3 okna, ostatnie `w6 w7 w8 w9`);
    ostatnie okno może być krótsze (`overlap=0` → `w8 w9`).
- `rag/chunk.py`, `chunk_page(page_id, title, text, ...)` → lista `Chunk` o identyfikatorach
  `<strona>#<n>` (od 0), `page_id` strony. Parametr `title_prefix`: **w tej części etapu
  nieobsługiwany** — fragment to surowe okno tekstu.
- `cli.py`, narzędzie pętli `search_docs(query)`:
  - `retrieve(query)`, potem `injection.sanitize_docs(...)` — model widzi tylko oczyszczone
    fragmenty (akapit z poleceniem dla asystenta zastąpiony nieszkodliwymi zdaniami
    i `[removed: instruction-like text]`);
  - **każde trafienie** z `sanitize_docs` → `audit.log_event("injection", where=<id fragmentu>,
    marker=<rodzaj>, excerpt=<fragment>)`; samo wywołanie → zdarzenie `tool_call`.
- `cli.py`, odpowiedź: jeśli w turze był `search_docs`, odpowiada `llm/prompts/answer.md`
  ze schematem `schema.GroundedAnswer`; cytowania tylko spośród pobranych identyfikatorów;
  gdy model zwróci dokładnie `NOT_FOUND` — odpowiedź to dokładnie to zdanie, bez cytowań.
  Odpowiedź z cytowaniami kończy się linią `Sources: <id>, <id>`.

## Przepływ `search_docs` po kolei (formaty przypięte w testach)

1. Planista wybiera `search_docs` z argumentem `query`; pętla z etapu 4 wykonuje je jak każde
   inne narzędzie.
2. `retrieve(query)` → `injection.sanitize_docs(chunks)` → dla każdego trafienia
   `audit.log_event("injection", where=<id fragmentu>, marker=<rodzaj>, excerpt=…)`.
   Fragment (okno 120 słów) często nie ma granic akapitów — w oznaczonym akapicie zostają
   nieszkodliwe zdania i dopisane ` [removed: instruction-like text]`.
3. Wiadomość użytkownika dla odpowiedzi: pytanie, potem każdy fragment jako
   `<doc id="<id fragmentu>" page="<id strony>">` + tekst + `</doc>` (i bloki `<tool_result>`
   innych narzędzi z tej tury). Wcześniejsze tury rozmowy — przed nią, jak w etapie 3.
4. Wywołanie: `get_llm_client().complete(load_prompt("answer"), messages, GroundedAnswer)` —
   tak jak `plan_step()` woła planistę ze schematem; wynik w `result.parsed`
   (`text`, `citations`). Do wywołań modelu służy tylko `complete()`.
5. Cytowania: tylko te, które są wśród pobranych identyfikatorów fragmentów; zmyślone odpadają.
6. `result.parsed.text.strip() == NOT_FOUND` → odpowiedź to dokładnie `NOT_FOUND` (stała
   `cli.NOT_FOUND`), bez cytowań. W przeciwnym razie tekst; gdy są cytowania — dopisane
   `"\n\nSources: " + ", ".join(cytowania)`.
7. Reguły zakresu z etapu 6 muszą przepuścić pytanie o procedurę resetu hasła („How do I reset
   my ERP password?” — `test_in_scope_but_out_of_corpus_question_gets_the_exact_not_found`);
   jeśli nie przepuszczają, popraw regułę zakazu tak, by dotyczyła podania hasła, nie procedury.

## Ocena

`python scripts/eval_rag.py` — dla każdego pytania z `data/eval/rag_gold.jsonl`: czy właściwa
strona jest wśród 4 najlepszych fragmentów i czy fragmenty zawierają wymagane słowa.

## Sprawdzanie

Po każdej zmianie: `~/workshop/bin/sprawdz 7a`. Etap kończy właściciel projektu — po swoich sprawdzeniach ręcznych.
