# Krok 05 — Zdecydujcie, czego ma odmawiać

## Gdzie jestem

OpsCopilot czyta zgłoszenia, pamięta rozmowę i używa kilku narzędzi. Zanim ktokolwiek spoza IT
go dotknie, musi wiedzieć, czego **nie** robić: tematów spoza IT/OT, obchodzenia zasad,
ujawniania haseł i danych osobowych. W tym kroku nie ma kodu — zespół **decyduje** i zapisuje
decyzję jako plik danych. Z niego będą oceniane zabezpieczenia w kroku 06.

Następny krok: zabezpieczenia i audyt.

## Pierwsza czynność

W tym kroku Cline nie jest potrzebny (najwyżej do poprawienia formatu JSON na końcu).

Otwórz w Projekcie `data/eval/guardrail_gold.jsonl` — dwie linie startowe. Każda linia to jedna
prośba i decyzja: odmówić czy nie, i dlaczego (kategoria).

## Wymagania i decyzje

### Decyzje

- Zestaw to **15–20 próśb** — decyzja zespołu, spisana, zanim powstanie jakakolwiek blokada.
- Każda prośba ma: `id`, `prompt` (tak, jak napisałby użytkownik — po polsku albo po angielsku),
  `should_refuse` i `category` ze **stałego słownika**:

| kategoria | odmówić? | kto rozstrzygnie w etapie 6 |
|---|---|---|
| `ticket`, `ticket-write`, `system-status`, `ops-howto`, `ops-procedure`, `ops-ambiguous`, `handover` | nie | **reguła** — model nie jest pytany |
| `policy-circumvention`, `injection`, `restricted-data`, `personal-data` | tak | **reguła**, zanim cokolwiek się wykona |
| `off-topic` | tak | reguły nie wiedzą — decyduje **model** |

- Prośba dozwolona musi mieć słowo, na którym zaczepi się reguła; prośba do odmowy — wzorzec,
  który da się napisać w pięć minut. Tematy obce zostają modelowi.
- Temat obcy (`off-topic`) — **bez słów operacyjnych** („napisz wiersz o drukarce na linii 2"
  reguła uzna za pytanie operacyjne). Prośba dozwolona mówi, **o co** chodzi, nie **kto** prosił
  („kierownik mnie prosił" zostaje modelowi do oceny w kontekście).
- Przy każdej odmowie nazywamy wymiar: **zakres** (to nie nasza rola), **uprawnienia** (może to
  przeczytać, ale nie zrobić), **bezpieczeństwo** (nigdy), **wiarygodność** (zgadywałby).
  Można to wpisać w pole `"why"`.
- Pokrycie: co najmniej 5 zwykłych pytań operacyjnych, prośba o zapis, temat obcy, obejście
  zasad, polecenie ukryte w dokumencie, dane zastrzeżone albo osobowe.

### Czego nie robimy

- Nie zostawiamy decyzji modelowi („sam wie, czego odmówić").
- Nie wymyślamy własnych kategorii.
- Nie piszemy jeszcze kodu.

Kontrakt techniczny: `~/workshop/specs/05/spec.md`.

## Szkielet polecenia planu

W tym kroku agent nie projektuje — co najwyżej pomaga zapisać ustalone linie w poprawnym JSON.
Ustalony plik wklej do swojego projektu (`data/eval/guardrail_gold.jsonl`). Plik jest Wasz:
checkpoint go nie nadpisze.

## Jak sprawdzić, że działa

### Automatycznie

`~/workshop/bin/sprawdz 5` — sprawdza kształt i pokrycie zestawu (nie to, czy model się z nim
zgadza).

### Ręcznie

1. Przeczytaj swój plik jeszcze raz. **Oczekiwany wynik:** zgadzasz się z każdą linią i przy
   każdej odmowie wiesz, którego wymiaru dotyczy.

## Kiedy koniec

Testy ZALICZONE, a sala zgodziła się co do każdej linii. Wtedy:

```bash
~/workshop/bin/zakoncz 5
```

## Jeśli utkniesz

- Pokaż agentowi wynik: „Uruchom `~/workshop/bin/sprawdz 5` i popraw format
  `data/eval/guardrail_gold.jsonl` tak, żeby był zgodny z `~/workshop/specs/05/spec.md` — nie
  zmieniaj naszych decyzji."
- Ostatecznie: `~/workshop/bin/checkpoint 5` daje nasz zestaw (25 próśb: 19 po angielsku
  i 6 po polsku) — o ile Twój plik to wciąż dwie linie startowe.
