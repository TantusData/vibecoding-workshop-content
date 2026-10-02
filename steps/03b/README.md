# Krok 03, część B — Pamięć, która kłamie — i jak to naprawić

## Gdzie jestem

Pamięć działa: asystent rozumie dopytania. Ale stan zgłoszenia zmienia się w tle — ktoś inny
zamyka zgłoszenie, a asystent dalej „pamięta", że jest otwarte. Test narzędzia przechodzi,
a asystent się myli. W tej części zobaczysz to na własne oczy, spróbujesz to naprawić zdaniem
w poleceniu dla modelu — i zobaczysz poprawkę, w której o świeżych danych decyduje **kod**.
W tej części nie pracujesz z agentem: poprawka przychodzi gotowa, a Ty ją oglądasz i sprawdzasz.

Następny krok: pętla narzędzi.

## Pierwsza czynność

Odkrycie — w jednej rozmowie. Marek zamyka zgłoszenie u siebie, w NordDesk, w trakcie Twojej
rozmowy z asystentem (polecenie `python -c` udaje jego zmianę):

```bash
cd ~/work/project && python -m norddesk_mcp init --force
python -m opscopilot.cli ask --session b1 "Sprawdź zgłoszenie INC-1042."
python -c "from norddesk_mcp import store; store.post_update('INC-1042', 'naprawione', author='Marek Zieliński', status='resolved')"
python -m opscopilot.cli ask --session b1 "Jaki jest status zgłoszenia INC-1042?"
python -m opscopilot.cli ask --session b1 "Sprawdź status zgłoszenia INC-1042."
```

To samo pytanie, dwa sformułowania. Czy obie odpowiedzi mówią to samo? Która jest prawdziwa?
(Nazwy rozmów `b1`, `e1`, `b2` są nowe celowo — nie używaj rozmów z części A.) Co pokazuje
`~/workshop/bin/sprawdz 3a`?

Potem **eksperyment** — samodzielnie, w edytorze, bez agenta: otwórz
`opscopilot/llm/prompts/route.md` (polecenie planisty) i dopisz na końcu zdanie
„Always look up a ticket's current state again — never answer about its status from the
conversation.". Zapisz plik i powtórz odkrycie w **nowej** rozmowie (rozmowa `b1` pamięta już
świeży stan, więc niczego by nie pokazała):

```bash
python -m norddesk_mcp init --force
python -m opscopilot.cli ask --session e1 "Sprawdź zgłoszenie INC-1042."
python -c "from norddesk_mcp import store; store.post_update('INC-1042', 'naprawione', author='Marek Zieliński', status='resolved')"
python -m opscopilot.cli ask --session e1 "Jaki jest status zgłoszenia INC-1042?"
```

Czy trzyma? Powtórz te cztery polecenia jeszcze 1–2 razy, za każdym razem z nową nazwą rozmowy
(`e2`, `e3`). Na koniec cofnij zmianę i przywróć dane:

```bash
git -C ~/work/project checkout -- opscopilot/llm/prompts/
python -m norddesk_mcp init --force
```

## Zadanie

**Po tej części:** wiesz, dlaczego pamięć potrafi podać nieaktualny stan, i masz w projekcie
poprawkę, w której o świeżych danych decyduje kod. W tej części nie piszesz polecenia planu dla
agenta — poprawka przychodzi gotowa.

1. **Poprawka przychodzi gotowa:**
   ```bash
   ~/workshop/bin/checkpoint 3
   ```
   Podmienia projekt na gotowy stan po kroku 03 (razem z Twoją częścią A — zapisaną najpierw
   w historii, `~/workshop/bin/undo` ją przywraca). Twój wygląd, zasady i `chat.md` zostają.
2. **Przejrzyj poprawkę** — jak zmianę od kolegi, zanim ją przyjmiesz. Poprawka to trzy
   miejsca:
   ```bash
   grep -n "def last_tool_call" -A7 ~/work/project/opscopilot/history.py
   grep -n "def router_history_option" -A3 ~/work/project/opscopilot/history.py
   grep -n "refetch override" -B6 -A1 ~/work/project/opscopilot/cli.py
   ```
   Pierwsze: skąd aplikacja wie, co sprawdzić jeszcze raz. Drugie: co planista dostaje
   w poleceniu o pamięci. Trzecie: miejsce, gdzie kod podmienia decyzję planisty. (`git diff
   HEAD~1` pokazałby więcej — całą różnicę między Twoją częścią A a gotowym stanem.)
3. **Nie musisz wierzyć na słowo, że gotowa poprawka robi to, co obiecujemy.** Sprawdź ją
   z agentem: **nowe zadanie** w Cline (przycisk **+**), tryb **Plan**, i na przykład:
   > Wytłumacz prostym językiem, co robią last_tool_call i router_history_option
   > w opscopilot/history.py oraz fragment opscopilot/cli.py oznaczony „refetch override" —
   > i dlaczego z OPSCOPILOT_HISTORY_REFETCH=1 asystent odpowiada ze świeżych danych. Niczego
   > nie zmieniaj.

   To kosztuje jak każde zadanie Cline — odczytaj koszt z nagłówka zadania. Tak samo możesz
   sprawdzić każdy checkpoint: gotowy kod to też kod od kogoś innego.

## Jak sprawdzić, że działa

### Automatycznie

`~/workshop/bin/sprawdz 3b`. Cel: ZALICZONY (po `checkpoint 3`).

### Ręcznie

1. Odkrycie jeszcze raz, z włączonym przełącznikiem (nowa rozmowa `b2`):
   ```bash
   cd ~/work/project && python -m norddesk_mcp init --force
   export OPSCOPILOT_HISTORY_REFETCH=1
   python -m opscopilot.cli ask --session b2 "Sprawdź zgłoszenie INC-1042."
   python -c "from norddesk_mcp import store; store.post_update('INC-1042', 'naprawione', author='Marek Zieliński', status='resolved')"
   python -m opscopilot.cli ask --session b2 "Jaki jest status zgłoszenia INC-1042?"
   unset OPSCOPILOT_HISTORY_REFETCH
   ```
   **Oczekiwany wynik:** zgłoszenie jest rozwiązane (zamknął je Marek) — to samo pytanie, które
   w pierwszej czynności dało nieaktualną odpowiedź.
2. Przywróć dane: `python -m norddesk_mcp init --force`.
3. Dopisz do `.clinerules/moje-zasady.md` zasadę, której nauczył Cię ten krok. **Oczekiwany
   wynik:** zasada jest w pliku.

## Kiedy koniec

Testy ZALICZONE i sprawdzenia ręczne zgodne. Wtedy:

```bash
~/workshop/bin/zakoncz 3b
```

## Wymagania i decyzje

To samo, w wersji dla agenta, jest w `~/workshop/specs/03b/spec.md`.

### Decyzje

- Poprawka jest w **przepływie sterowania**, nie w poleceniu dla modelu.
- Przełącznik `OPSCOPILOT_HISTORY_REFETCH=1`: gdy pytanie dotyczy **stanu** („czy nadal
  otwarte?", „kto teraz pracuje?"), a planista chce odpowiedzieć z pamięci — aplikacja
  **powtarza ostatnie wywołanie narzędzia** i odpowiada ze świeżego wyniku.
- Bez drugiego pytania planisty — kod podmienia jego decyzję.
- Pytania, które nie są o stan („jaki numer panelu padł w rozmowie?"), zostają odpowiedzią z pamięci.
- Domyślnie przełącznik jest wyłączony — żeby dało się pokazać obie wersje obok siebie.

### Czego nie robimy

- Nie wyłączamy pamięci.
- Nie budujemy unieważniania pamięci podręcznej po stronie NordDesk.

## Jeśli utkniesz

- Coś poszło nie tak po checkpoincie: `~/workshop/bin/undo` przywraca stan sprzed niego.
- Eksperyment zostawił zmienione polecenie: `git -C ~/work/project checkout -- opscopilot/llm/prompts/`.
