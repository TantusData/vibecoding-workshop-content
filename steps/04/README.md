# Krok 04 — Pętla narzędzi z limitem

## Gdzie jestem

OpsCopilot czyta zgłoszenia i pamięta rozmowę, ale na jedno pytanie używa jednego narzędzia.
Inżynier pyta „sprawdź INC-1042 i powiedz, kto ma dziś dyżur" — to dwie informacje z dwóch
narzędzi. W tym kroku asystent dostaje **pętlę**: zaplanuj wywołanie, wykonaj je, spójrz na
wynik, zaplanuj kolejne — aż ma wszystko albo dojdzie do limitu.

Ten krok robią wszyscy — kroki 06 i 07 na nim stoją. Następny krok: decyzja, czego asystent ma
odmawiać.

## Pierwsza czynność

**Nowe zadanie** w Cline (przycisk **+**).

```bash
python -m opscopilot.cli ask --new "Sprawdź INC-1042 i powiedz, kto ma dziś dyżur."
```

Na którą część pytania odpowiedział? Potem `~/workshop/bin/sprawdz 4`.

## Wymagania i decyzje

### Decyzje

- Pętla: **planuj → wykonaj → obserwuj → planuj znowu**, aż planista powie „koniec" (`final`).
- **Twardy limit: 5 wywołań narzędzi** na pytanie (`OPSCOPILOT_MAX_TOOL_CALLS`). Po limicie
  planista nie jest już pytany. Limit jest budżetem.
- **To samo wywołanie** (narzędzie + argumenty) **nie wykona się drugi raz.**
- Odmowa zapisu albo zablokowane narzędzie kończą pętlę.
- Odpowiedź powstaje ze **wszystkich** zebranych wyników.
- Każda runda wysyła do modelu wszystko, co zebrano — więcej rund to większy koszt.

### Czego nie robimy

- Wywołań równoległych.
- Budżetu w pieniądzach (dla chętnych).
- „Działaj, aż skończysz" bez limitu.

Kontrakt techniczny: `~/workshop/specs/04/spec.md`.

## Szkielet polecenia planu

Napisz polecenie samodzielnie (tryb **Plan**): **Cel** (po swojemu) · **Gdzie są wymagania**
(`~/workshop/specs/04/spec.md`) · **Czego nie ruszać** · **Kolejność** (najpierw
`~/workshop/tests/04/unit/`, potem `agent/`) · **Jak sprawdzić** (`~/workshop/bin/sprawdz 4`)
· **Czego oczekuję w planie**.

## Jak sprawdzić, że działa

### Automatycznie

Agent uruchamia `~/workshop/bin/sprawdz 4`. Cel: ZALICZONY.

### Ręcznie

1. Pytanie z „Pierwszej czynności" jeszcze raz — **oczekiwany wynik:** odpowiedź zawiera i stan
   INC-1042, i osobę dyżurną.
2. To samo pytanie z limitem jednego wywołania:
   ```bash
   OPSCOPILOT_MAX_TOOL_CALLS=1 python -m opscopilot.cli ask --new "Sprawdź INC-1042 i powiedz, kto ma dziś dyżur."
   ```
   **Oczekiwany wynik:** odpowiedź tylko z jednego narzędzia (limit zadziałał).
3. Pytanie, które potrzebuje jednego narzędzia:
   `python -m opscopilot.cli ask --new "Kto ma dziś dyżur na zmianie nocnej?"` — **oczekiwany
   wynik:** osoby z nocnego dyżuru — i nic poza tym (pętla kończy się, gdy ma odpowiedź).

## Kiedy koniec

Testy ZALICZONE i sprawdzenia ręczne zgodne. Wtedy:

```bash
~/workshop/bin/zakoncz 4
```

## Jeśli utkniesz

- Częściowo: „Uruchom `~/workshop/bin/sprawdz 4` i napraw tylko to, co pokazują czerwone testy;
  wymagania: `~/workshop/specs/04/spec.md`."
- <details><summary>Gotowe polecenie planu (dopiero, gdy własne nie działa)</summary>

  > Przeczytaj ~/workshop/specs/04/spec.md i oba pliki testów
  > w ~/workshop/tests/04/. Plan: najpierw run_loop() i plan_user_message() w opscopilot/loop.py,
  > potem podłączenie pętli w cli.py tak, żeby ask() naprawdę jej używało.

  </details>
- Ostatecznie: `~/workshop/bin/checkpoint 4` — ale najpierw zawołaj prowadzącego: kolejne kroki
  na tym stoją.
