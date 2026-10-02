# Krok 07, część B — Dlaczego nie znalazł? Jakość wyszukiwania

## Gdzie jestem

Asystent odpowiada z wiki i podaje źródła. Ale jakość odpowiedzi zależy od tego, **co zostanie
znalezione** — model nie odpowie dobrze z fragmentu, który do niego nie trafił. W tej części
sprawdzisz, jak wyglądają fragmenty strony o paletyzatorze KX-90, i poprawisz dzielenie tak,
żeby każdy fragment wiedział, z jakiej strony pochodzi.

Następny krok: gotowa całość.

## Pierwsza czynność

**Nowe zadanie** w Cline (przycisk **+**).

Odkrycie — obejrzyj fragmenty strony o KX-90 (bez żadnych dodatków):

```bash
python -c "from nordwiki_mcp import corpus; from opscopilot.rag.chunk import chunk_page; p=corpus.get_page('palletiser-kx90-maintenance'); [print(c.id, 'KX-90' in c.text, c.text[:80]) for c in chunk_page(p['id'], p['title'], p['content'], title_prefix=False)]"
```

Druga kolumna mówi, czy fragment zawiera nazwę maszyny. Który fragment opisuje blokadę panelu
(schładzanie, zatwierdzenie)? Czy zawiera słowo „KX-90"? Co z tego wynika, gdy ktoś pyta
„jak otworzyć panel **KX-90**"?

Potem:

```bash
python -m opscopilot.cli ask --new "Ile trwa schładzanie przed otwarciem panelu napędu KX-90 i kto musi to zatwierdzić?"
python scripts/eval_rag.py
```

## Wymagania i decyzje

### Decyzje

- **Każdy fragment zaczyna się od tytułu swojej strony** (`„<tytuł> — …"`). Fragment o blokadzie
  panelu mówi wtedy, że dotyczy KX-90.
- Włącza to ustawienie `RAG_TITLE_PREFIX` (domyślnie włączone); wyłączone — surowe fragmenty,
  do porównania.
- Po zmianie indeks przebudowuje się sam.
- Jakość wyszukiwania mierzymy zestawem pytań (`scripts/eval_rag.py`), nie wrażeniem.

### Czego nie robimy

- Nie zmieniamy modelu na większy — problem jest w danych, które do niego trafiają.
- Nie dokładamy ponownego rankingu fragmentów (reranker).

Kontrakt techniczny: `~/workshop/specs/07b/spec.md`.

## Szkielet polecenia planu

Napisz polecenie samodzielnie (tryb **Plan**): **Cel** (po swojemu) · **Gdzie są wymagania**
(`~/workshop/specs/07b/spec.md`) · **Czego nie ruszać** · **Kolejność** (najpierw
`~/workshop/tests/07b/unit/`, potem `agent/`) · **Jak sprawdzić** (`~/workshop/bin/sprawdz 7b`)
· **Czego oczekuję w planie**.

## Jak sprawdzić, że działa

### Automatycznie

Agent uruchamia `~/workshop/bin/sprawdz 7b`. Cel: ZALICZONY.

### Ręcznie

1. Polecenie z „Pierwszej czynności", ale z `title_prefix=True` — **oczekiwany wynik:** każdy
   fragment zawiera „KX-90".
2. Pytanie o KX-90 jeszcze raz — **oczekiwany wynik:** 20 minut schładzania, zatwierdzenie
   drugiej uprawnionej osoby, ze źródłem (`palletiser-kx90-maintenance#…`). Odpowiedź mogła być
   dobra już przed poprawką — model łapie sens bez nazwy maszyny. Różnicę widać w punkcie 3.
3. Co dostaje model — 4 fragmenty do pytania o KX-90, z poprawką i bez:
   ```bash
   python -c "from opscopilot.rag.retrieve import retrieve; [print(c.id, round(c.score,3), c.text[:45]) for c in retrieve('Ile trwa schładzanie przed otwarciem panelu napędu KX-90?')]"
   RAG_TITLE_PREFIX=0 python -c "from opscopilot.rag.retrieve import retrieve; [print(c.id, round(c.score,3), c.text[:45]) for c in retrieve('Ile trwa schładzanie przed otwarciem panelu napędu KX-90?')]"
   ```
   **Oczekiwany wynik:** z poprawką wszystkie 4 miejsca zajmuje procedura blokady, a wynik
   fragmentu `#8` jest wyższy; bez poprawki jedno miejsce zabiera wstęp podręcznika (`#0`), który
   o schładzaniu nic nie mówi. Każde polecenie przebudowuje indeks — chwilę trwa. Dla chętnych:
   `python scripts/eval_rag.py` z `RAG_TITLE_PREFIX=0` i bez — ocenia tylko trafienie strony,
   więc obie wersje wyjdą podobnie.
4. Dopisz do `.clinerules/moje-zasady.md` zasadę, której nauczył Cię ten krok, potem
   **nowe zadanie** w Cline (agent czyta zasady na początku zadania). **Oczekiwany wynik:** zasada
   jest w pliku.

## Kiedy koniec

Testy ZALICZONE i sprawdzenia ręczne zgodne. Wtedy:

```bash
~/workshop/bin/zakoncz 7b
```

## Jeśli utkniesz

- Częściowo: „Uruchom `~/workshop/bin/sprawdz 7b` i napraw tylko to, co pokazują czerwone testy;
  wymagania: `~/workshop/specs/07b/spec.md`."
- <details><summary>Gotowe polecenie planu (dopiero, gdy własne nie działa)</summary>

  > Przeczytaj ~/workshop/specs/07b/spec.md i testy
  > w ~/workshop/tests/07b/. Plan: obsługa title_prefix w chunk_page (domyślnie z ustawienia
  > RAG_TITLE_PREFIX), tak żeby indeks przebudował się po zmianie.

  </details>
- Ostatecznie: `~/workshop/bin/checkpoint 7`.
