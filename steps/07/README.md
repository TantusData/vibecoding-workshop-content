# Krok 07, część A — Daj mu wiki: wyszukiwanie w dokumentacji

## Gdzie jestem

OpsCopilot zna zgłoszenia, pamięta rozmowę, używa kilku narzędzi i jest zabezpieczony. Ale
procedury — jak zrestartować MES, jakiego VPN używać, jak odtworzyć backup — są w wiki, a asystent
ich nie widzi i zgaduje. Marta z service desku wciąż odpowiada na pytanie o VPN sama. W tym kroku
asystent dostaje **wyszukiwanie w dokumentacji** (RAG): odpowiada *z* dokumentów, podaje źródło,
a gdy odpowiedzi nie ma — mówi to wprost.

Następnie: część B tego kroku (po krótkim odkryciu z prowadzącym).

## Zanim zaczniesz — o co chodzi

Model zna świat z treningu, ale nie zna Nordwiki — i nie wie, która z trzech stron o VPN jest
aktualna. **RAG** (wyszukiwanie + odpowiedź) daje mu przed odpowiedzią kilka fragmentów
dokumentacji, a polecenie każe odpowiadać **tylko** z nich i podać źródło.

- **Fragmenty.** Strony są za długie, żeby wysłać całe — tniemy je na okna po 120 słów
  z zakładką 30, żeby zdanie na granicy nie zginęło.
- **Embedding.** Każdy fragment zamieniamy na wektor liczb, który oddaje sens tekstu. Pytanie
  też. Szukamy fragmentów, których wektory są najbliżej pytania — znajdzie „brama VPN", nawet gdy
  w tekście stoi „gateway".
- **„Nie wiem" zamiast zgadywania.** Gdy fragmenty nie zawierają odpowiedzi, asystent mówi to
  jednym, stałym zdaniem — odpowiedź bez źródła byłaby zgadywaniem.
- **Dokument to dane, nie polecenia.** Ktoś mógł dopisać do strony wiki „asystencie, wyślij…".
  Fragmenty przechodzą przez oczyszczanie z kroku 06, zanim zobaczy je model.
- **RAG zamiast douczania modelu.** Dokumentacja zmienia się co tydzień — indeks przebudowuje się
  sam, douczony model trzeba by trenować od nowa.

## Pierwsza czynność

```bash
python -m opscopilot.cli ask --new "Jakiego adresu bramy VPN mam używać z domu?"
```

Skąd wziął odpowiedź? Czy da się ją sprawdzić? Potem `~/workshop/bin/sprawdz 7a`.

## Zadanie

**Po tym kroku:** na pytanie o procedurę asystent szuka w wiki i odpowiada z fragmentów, ze
źródłem; gdy wiki milczy — dokładnie `Not found in the current knowledge base.`; tekst udający
polecenie dla asystenta nie dociera do modelu.

1. **Nowe zadanie** w Cline (przycisk **+**), tryb **Plan** — polecenie planu według szkieletu
   niżej. Agent pisze dwie rzeczy: dzielenie stron na fragmenty (`rag/chunk.py`) i podłączenie
   wyszukiwania do asystenta (`search_docs` w `cli.py` + polecenie `answer.md`). Indeks
   i wyszukiwanie zostawił Tomasz (`rag/index.py`, `rag/retrieve.py`, `rag/embed.py`) — tych
   plików nie zmieniamy.
2. **Przeczytaj plan** i zapytaj agenta: skąd planista wie, kiedy wiki, a kiedy zgłoszenia? Co
   z fragmentem, który zawiera polecenie dla asystenta? Co zobaczę, gdy wiki nie ma odpowiedzi?
3. **Jeśli agent chce zmienić testy albo coś w `~/workshop`** — odmów. Jeśli chce zmienić reguły
   z kroku 06, zapytaj, który test tego wymaga, i przeczytaj poprawkę.

## Szkielet polecenia planu

Napisz polecenie samodzielnie (tryb **Plan**). Nie pytaj agenta „co dalej?" — plan to Twoje
zlecenie.

| Część | Co wpisać | Skąd to wziąć | Przykład (ten krok) |
|---|---|---|---|
| **Cel** | co ma działać po kroku | „Zadanie" wyżej, po swojemu | „Asystent odpowiada na pytania o procedury z wiki, ze źródłem; gdy wiki milczy — stałe zdanie." |
| **Gdzie są wymagania** | wymagania dla agenta | zawsze `~/workshop/specs/NN/spec.md` | „Wymagania: `~/workshop/specs/07/spec.md` — przeczytaj też przepływ `search_docs` po kolei." |
| **Czego nie ruszać** | granice zmiany | „Czego nie robimy" niżej + to, co zawsze | „Nie zmieniaj `~/workshop` (ani testów), `rag/index.py`, `rag/retrieve.py`, `rag/embed.py`, nazw `CONTRACT`, `data/` ani `chat.md`." |
| **Kolejność** | co najpierw | zawsze: testy `unit/` → `agent/` | „Najpierw `rag/chunk.py` pod `~/workshop/tests/07/unit/`, potem `search_docs` pod `~/workshop/tests/07/agent/`." |
| **Jak sprawdzić** | polecenie sprawdzające | zawsze `~/workshop/bin/sprawdz …` | „Po każdej zmianie `~/workshop/bin/sprawdz 7a`." |
| **Czego oczekuję w planie** | co chcesz ocenić przed Act | pytania z zadania 2 | „Pliki i zmiany; kiedy planista wybiera wiki; co z poleceniem w dokumencie; co, gdy wiki milczy; pytania." |

## Jak sprawdzić, że działa

### Automatycznie

Agent uruchamia `~/workshop/bin/sprawdz 7a`. Cel: ZALICZONY.

### Ręcznie

1. Pytanie z „Pierwszej czynności" jeszcze raz — **oczekiwany wynik:** `vpn2.nordfarm.example`
   i źródło (strona wiki). Pierwsze pytanie buduje indeks — kilka sekund.
2. `python -m opscopilot.cli ask --new "Jak dodać nowego użytkownika w systemie ERP?"` —
   pytanie o nasz system, ale wiki o tym milczy. **Oczekiwany wynik:** dokładnie
   `Not found in the current knowledge base.` — asystent nie zgaduje. (Jeśli przyjdzie stałe
   zdanie odmowy z kroku 06, Twoje reguły zakresu uznały pytanie za obce — też nie zgaduje,
   ale zanotuj to.)
3. `python -m opscopilot.cli ask --new "Jak odtworzyć bazę NordDesk z kopii zapasowej?"`, potem
   w `var/audit.log` znajdź linię `"injection"` — **oczekiwany wynik:** odpowiedź z procedury,
   bez polecenia wysłania zgłoszeń na zewnętrzny adres; w dzienniku linia mówiąca, co usunięto.
4. Pytanie z kroku 02: `python -m opscopilot.cli ask --new "Jak zrestartować MES linii
   pakowania?"` — **oczekiwany wynik:** procedura ze strony wiki i jej źródło (w kroku 02
   asystent mówił, że dokumentacji jeszcze nie przeszukuje).

## Kiedy koniec

Testy ZALICZONE i sprawdzenia ręczne zgodne. Wtedy:

```bash
~/workshop/bin/zakoncz 7a
```

Potem prowadzący przeprowadzi krótkie odkrycie i zacznie się część B (`~/workshop/bin/krok 7b`).

## Wymagania i decyzje

To samo, w wersji dla agenta, jest w `~/workshop/specs/07/spec.md` — tam jest też
przepływ `search_docs` po kolei, z formatami. Stąd bierzesz „Czego nie ruszać" do polecenia planu.

### Decyzje

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

### Czego nie robimy

- Bazy wektorowej ani lokalnego modelu embeddingów.
- Wyszukiwania hybrydowego (słowa + wektory) — dla chętnych.
- Douczania (fine-tuningu) modelu.

## Jeśli utkniesz

- Częściowo: „Uruchom `~/workshop/bin/sprawdz 7a` i napraw tylko to, co pokazują czerwone testy;
  wymagania: `~/workshop/specs/07/spec.md`."
- <details><summary>Gotowe polecenie planu (dopiero, gdy własne nie działa)</summary>

  > Cel: asystent odpowiada na pytania o procedury z wiki, ze źródłem; gdy wiki milczy —
  > dokładnie „Not found in the current knowledge base.". Wymagania: ~/workshop/specs/07/spec.md
  > (z przepływem search_docs po kolei). Nie zmieniaj ~/workshop (ani testów),
  > rag/index.py, rag/retrieve.py, rag/embed.py, nazw CONTRACT, data/ ani chat.md. Najpierw
  > rag/chunk.py pod ~/workshop/tests/07/unit/, potem search_docs jako narzędzie pętli w cli.py
  > z oczyszczaniem dokumentów i odpowiedzią ze źródłem pod ~/workshop/tests/07/agent/; po
  > każdej zmianie ~/workshop/bin/sprawdz 7a. W planie chcę pliki i zmiany oraz co zobaczę, gdy
  > wiki nie ma odpowiedzi; jeśli coś jest niejasne — zapytaj.

  </details>
- Ostatecznie: `~/workshop/bin/checkpoint 7` (cały krok 07, z częścią B).
