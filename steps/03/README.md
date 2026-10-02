# Krok 03, część A — Niech pamięta rozmowę

## Gdzie jestem

OpsCopilot czyta NordDesk, ale każde pytanie traktuje jak pierwsze. Inżynier zmiany pyta
„sprawdź INC-1042", a zaraz potem „a kto nad nim pracuje?" — i asystent nie wie, o co chodzi.
W tym kroku asystent dostaje **pamięć rozmowy**: ostatnie wiadomości sesji, zapisane w bazie
i oddawane modelowi przy kolejnym pytaniu.

Następnie: część B tego kroku (po krótkim odkryciu z prowadzącym).

## Pierwsza czynność

**Nowe zadanie** w Cline (przycisk **+**).

Przywróć dane NordDesk i zadaj dwa pytania w jednej rozmowie:

```bash
cd ~/work/project && python -m norddesk_mcp init --force
python -m opscopilot.cli ask --session demo "Sprawdź zgłoszenie INC-1042."
python -m opscopilot.cli ask --session demo "A kto nad nim pracuje?"
```

Opcja `--session` jest od Tomasza, ale jeszcze niczego nie zapamiętuje. Czy drugie pytanie
zrozumiał? Potem `~/workshop/bin/sprawdz 3a`.

## Zadanie

**Po tym kroku:** w jednej rozmowie asystent rozumie dopytania bez numeru zgłoszenia („a kto nad
nim pracuje?", „a jaki ma priorytet?"); w innej rozmowie zaczyna od zera; możesz obejrzeć, co
pamięta (`python -m opscopilot.cli history show --session <nazwa>` — zawsze z
`python -m opscopilot.cli` na początku; samo `history` to polecenie powłoki).

1. **Pamięć rozmowy — z agentem.** Od tego kroku polecenie planu piszesz sam, według szkieletu
   niżej.
2. **Przeczytaj plan, zanim przełączysz na Act**, i zadaj agentowi dwa pytania:
   - Czy rozmowę zobaczy **i** planista (co sprawdzić), **i** odpowiedź? (Częsty błąd: tylko
     planista.)
   - Jak wpiszę nazwę rozmowy i jak obejrzę, co asystent pamięta? (`ask --session`,
     `history show --session`, `ask --new` — ich używasz w sprawdzeniach ręcznych.)
3. **Jeśli agent chce zmienić testy albo coś w `~/workshop`** — odmów. Testy odbiorcze są
   Twoją miarą; czerwony test znaczy, że do poprawy jest kod.

## Szkielet polecenia planu

Napisz polecenie samodzielnie (tryb **Plan**). Nie pytaj agenta „co dalej?" — plan to Twoje
zlecenie.

| Część | Co wpisać | Skąd to wziąć | Przykład (ten krok) |
|---|---|---|---|
| **Cel** | co ma się zmienić w rozmowie z asystentem | „Zadanie" wyżej, po swojemu | „Asystent ma pamiętać rozmowę: dopytanie bez numeru zgłoszenia działa w tej samej rozmowie, a w innej nie." |
| **Gdzie są wymagania** | ścieżka do wymagań dla agenta | zawsze `~/workshop/specs/NN/spec.md` | „Wymagania: `~/workshop/specs/03/spec.md`." |
| **Czego nie ruszać** | granice zmiany | „Czego nie robimy" niżej + to, co zawsze | „Nie zmieniaj `~/workshop` (ani testów), nazw `CONTRACT`, danych w `data/` ani `chat.md`." |
| **Kolejność** | co najpierw | zawsze: testy `unit/` → `agent/` | „Najpierw `~/workshop/tests/03/unit/`, potem `~/workshop/tests/03/agent/`." |
| **Jak sprawdzić** | polecenie sprawdzające | zawsze `~/workshop/bin/sprawdz …` | „Po każdej zmianie `~/workshop/bin/sprawdz 3a`." |
| **Czego oczekuję w planie** | co chcesz ocenić przed Act | dwa pytania z zadania 2 | „Lista plików i zmian; kto widzi rozmowę; jakie polecenia dostanę; pytania, jeśli coś jest niejasne." |

## Jak sprawdzić, że działa

### Automatycznie

Agent uruchamia `~/workshop/bin/sprawdz 3a`. Cel: ZALICZONY.

### Ręcznie

1. Dwa pytania z „Pierwszej czynności" jeszcze raz (nowa nazwa sesji, np. `--session demo2`).
   **Oczekiwany wynik:** drugie pytanie odpowiada o INC-1042.
2. `python -m opscopilot.cli history show --session demo2` — **oczekiwany wynik:** obie tury
   rozmowy, z wywołaniem narzędzia.
3. Trzecie pytanie w tej samej sesji: „A jaki ma priorytet?" — **oczekiwany wynik:** odpowiedź
   o INC-1042 bez podawania numeru.
4. To samo dopytanie w **innej** sesji:
   `python -m opscopilot.cli ask --session inna "A jaki ma priorytet?"` — **oczekiwany wynik:**
   asystent nie wie, o które zgłoszenie chodzi, i pyta o numer (pamięć jest per rozmowa).

## Kiedy koniec

Testy ZALICZONE i sprawdzenia ręczne zgodne. Wtedy:

```bash
~/workshop/bin/zakoncz 3a
```

Potem prowadzący przeprowadzi krótkie odkrycie i zacznie się część B (`~/workshop/bin/krok 3b`).

## Wymagania i decyzje

To samo, w wersji dla agenta, jest w `~/workshop/specs/03/spec.md`. Stąd bierzesz „Czego nie
ruszać" do polecenia planu.

### Decyzje

- Pamiętamy **ostatnie 20 wiadomości** rozmowy, w limicie ok. **6000 tokenów**; gdy się nie
  mieści, odpadają najstarsze całe wiadomości.
- Pamięć jest **per rozmowa** (sesja): `--session <nazwa>`; bez tej opcji — bieżąca rozmowa.
- Magazyn (SQLite) jest gotowy; piszemy logikę okna rozmowy.
- Stare wyniki narzędzi wracają do rozmowy w jednym z trzech trybów: `replay` (w całości,
  domyślnie), `drop` (bez nich), `summarise` (jednolinijkowy ślad).
- Rozmowę widzi **i** planista (co sprawdzić), **i** wywołanie odpowiedzi.
- Odmowa też jest częścią rozmowy (przyda się w etapie 6).

### Czego nie robimy

- Pamięci długoterminowej (faktów między rozmowami).
- Streszczania rozmowy modelem (dla chętnych).
- Gotowego frameworka pamięci.

## Jeśli utkniesz

- Częściowo: „Uruchom `~/workshop/bin/sprawdz 3a` i napraw tylko to, co pokazują czerwone testy;
  wymagania: `~/workshop/specs/03/spec.md`. Nie zmieniaj testów."
- <details><summary>Gotowe polecenie planu (dopiero, gdy własne nie działa)</summary>

  > Cel: asystent ma pamiętać rozmowę — dopytanie bez numeru zgłoszenia działa w tej samej
  > rozmowie, a w innej nie. Wymagania: ~/workshop/specs/03/spec.md. Nie zmieniaj ~/workshop
  > (także testów), nazw oznaczonych CONTRACT, danych w data/ ani opscopilot/llm/prompts/chat.md.
  > Najpierw opscopilot/history.py pod ~/workshop/tests/03/unit/, potem cli.py pod
  > ~/workshop/tests/03/agent/; po każdej zmianie ~/workshop/bin/sprawdz 3a. W planie chcę listę
  > plików i zmian, kto widzi rozmowę (planista i odpowiedź) i jakich poleceń użyję
  > (ask --session, history show --session, ask --new); jeśli coś jest niejasne — zapytaj.

  </details>
- Ostatecznie: `~/workshop/bin/checkpoint 3` (cały krok 03, z częścią B; cofnięcie:
  `~/workshop/bin/undo`).
