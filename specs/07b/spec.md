# Etap 7, część druga z planu Tomasza — Wyszukiwanie w wiki — jakość fragmentów

## Decyzje

- **Każdy fragment zaczyna się od tytułu swojej strony** (`„<tytuł> — …"`). Fragment o blokadzie
  panelu mówi wtedy, że dotyczy KX-90.
- Włącza to ustawienie `RAG_TITLE_PREFIX` (domyślnie włączone); wyłączone — surowe fragmenty,
  do porównania.
- Po zmianie indeks przebudowuje się sam.
- Jakość wyszukiwania mierzymy zestawem pytań (`scripts/eval_rag.py`), nie wrażeniem.

## Czego nie robimy

- Nie zmieniamy modelu na większy — problem jest w danych, które do niego trafiają.
- Nie dokładamy ponownego rankingu fragmentów (reranker).

## Etap 7, część druga — kontrakt: tytuł strony w każdym fragmencie

**Cel:** każdy fragment wie, z jakiej strony pochodzi — do pytania o KX-90 („ile trwa schładzanie
przed otwarciem panelu napędu KX-90 i kto musi to zatwierdzić?") wszystkie 4 najlepsze fragmenty
to procedura blokady KX-90 (20 minut schładzania, zatwierdzenie drugiej osoby).

**Testy:** `~/workshop/tests/07b/`.

## Kontrakt

- `rag/chunk.py`: `chunk_page(page_id, title, text, size=None, overlap=None, title_prefix=None)` —
  gdy `title_prefix` jest prawdziwe (domyślnie z ustawienia `RAG_TITLE_PREFIX`, =1), każdy
  fragment zaczyna się od `"<tytuł strony> — "`; gdy fałszywe — surowe okno.
- Indeks przebudowuje się sam, gdy zmienią się ustawienia albo kod `rag/chunk.py` (odcisk
  w `fingerprint()`).
- Porównanie: `retrieve()` z `RAG_TITLE_PREFIX=0` i bez (co dostaje model); `python
  scripts/eval_rag.py` ocenia tylko trafienie strony.

## Sprawdzanie

Po każdej zmianie: `~/workshop/bin/sprawdz 7b`. Etap kończy właściciel projektu — po swoich sprawdzeniach ręcznych.
