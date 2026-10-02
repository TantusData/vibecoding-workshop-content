# Krok 08 — Skończyliśmy projekt Tomasza

## Gdzie jestem

Trzy miesiące temu to była zaślepka i notatka. Dziś OpsCopilot czyta zgłoszenia, pamięta rozmowę
i nie wierzy pamięci bardziej niż systemowi, używa kilku narzędzi z limitem, odmawia tego, czego
nie powinien, nie zdradza haseł i odpowiada z dokumentacji ze źródłem. W tym kroku niczego nie
budujemy: pobierasz gotową wersję z dodatkami, które pokazują cały system — ślad każdej
odpowiedzi, koszty, poboczny projekt Tomasza — model uczenia maszynowego — jako narzędzie i
raport na koniec zmiany dla Marka.

## Pierwsza czynność

Pobierz gotową wersję (Twój wygląd, Twoje zasady i Twój zestaw testowy zostają):

```bash
~/workshop/bin/checkpoint 8
```

Masz czas i ochotę? **Najpierw** zrób zadanie „Dla chętnych" (niżej) — checkpoint weź potem.

## Dla chętnych — ślad i koszt z agentem (przed checkpointem, ~20–30 min)

Kierownik IT/OT chciał „widzieć, co asystent zrobił i ile to kosztowało". Wszystko, czego do tego
trzeba, już jest: każdy krok asystenta trafia do `var/audit.log` (od kroku 06), z kosztem
każdego wywołania modelu, a strona czatu ma prawy panel „Co zrobił system" — dziś pusty
(„Ta wersja aplikacji nie zapisuje jeszcze śladu"). Brakuje podłączenia. Polecenie planu napisz
**samodzielnie** — w trybie **Plan**, według szkieletu:

- **Cel** — po swojemu: pod każdą odpowiedzią widać kroki asystenta i koszt pytania.
- **Twoje decyzje** — 2–3 konkretne: co ma pokazać `python -m opscopilot.cli ask --trace "…"`
  w terminalu (kolejne kroki? czas każdego? koszt każdego wywołania modelu? suma za pytanie?),
  czego nie pokazywać (np. treści wyników narzędzi), czy dodać polecenie `usage` z sumą kosztów
  według etapu.
- **Gdzie są wymagania** — `~/workshop/specs/08/spec.md`, część „Ślad i koszt".
- **Czego nie ruszać** — `index.html` i `app.css` (panel już jest — wypełni się, gdy
  `ask_traced()` zwróci zdarzenia), `~/workshop`, dane w `data/`.
- **Jak sprawdzić** — ręcznie (niżej); testy kroku 08 sprawdzają dokładny format gotowej wersji
  i resztę dodatków — tu ich nie gonimy.
- **Czego oczekuję w planie** — lista zmian i to, jak będzie wyglądał wynik `--trace`, zanim
  cokolwiek zmienisz.

Sprawdź: `python -m opscopilot.cli ask --trace "Sprawdź INC-1042 i powiedz, kto ma dziś dyżur."`
— kroki (zakres → planista → narzędzia → odpowiedź) i suma kosztu według Twoich decyzji; to samo
pytanie na stronie czatu — panel po prawej pokazuje kroki. Potem `checkpoint 8`: podmieni ten kod
na gotową wersję (wygląd, zasady, `chat.md` i zestaw zostają) — porównaj obie.

## Wymagania i decyzje

### Decyzje

- **Ślad każdej odpowiedzi** pochodzi z dziennika audytu, nie z relacji modelu — widać go na
  stronie (prawy panel) i w terminalu (`ask --trace`).
- **Koszt każdego etapu** jest zapisywany (tokeny, kwota z bramki) — `usage`.
- **Model ML Tomasza staje się narzędziem** asystenta (`impact_estimate`): pytanie „jak
  poważne jest INC-1042?" kończy się liczbami z modelu, nie z modelu językowego.
- **Raport zmiany** w formacie Marka: dane zbierają narzędzia, model tylko pisze tekst według
  szablonu, a aplikacja sprawdza obowiązkowe nagłówki.

### Czego nie robimy

- Nie budujemy tych dodatków — oglądamy i oceniamy całość.

Kontrakt techniczny: `~/workshop/specs/08/spec.md`.

## Szkielet polecenia planu

W tym kroku nie ma polecenia dla agenta.

## Jak sprawdzić, że działa

### Automatycznie

`~/workshop/bin/sprawdz 8` — ZALICZONY.

### Ręcznie

1. Zrestartuj stronę (`Ctrl+C`, potem `python -m opscopilot.webapp`, panel Ports), zadaj pytanie
   i kliknij odpowiedź — **oczekiwany wynik:** po prawej ślad: kontrola zakresu, narzędzia,
   redakcje, wywołania modelu z tokenami i kosztem; Twój wygląd bez zmian.
2. `python -m opscopilot.cli ask --trace "Dlaczego INC-1042 ma priorytet P1 — jak poważne to jest?"`
   — **oczekiwany wynik:** odpowiedź z minutami przestoju i kwotą w EUR; w śladzie narzędzie
   `impact_estimate`.
3. Poboczny projekt Tomasza bez asystenta: `python -m opscopilot.cli impact INC-1042` —
   **oczekiwany wynik:** szacunek przestoju w minutach i kosztu w EUR oraz cztery czynniki, które
   go przesunęły (to liczby z modelu uczenia maszynowego, nie z modelu językowego).
4. Czy temu modelowi można ufać? `python scripts/train_impact.py --variant clean --eval`, potem
   `--variant shuffled --eval` i `--variant leaked --eval` — **oczekiwany wynik:** trzy różne
   wyniki R². Zanotuj, któremu wynikowi ufasz i dlaczego — omówimy to z prowadzącym. Nie pytaj
   o to agenta: to Twoja ocena.
5. `python -m opscopilot.cli usage` — **oczekiwany wynik:** tokeny i koszt per etap.
6. `python -m opscopilot.cli report --shift day` — **oczekiwany wynik:** podsumowanie zmiany
   z nagłówkami z `opscopilot/templates/handover.md`.
7. `python scripts/demo.py` — **oczekiwany wynik:** cały dzień w jednym przebiegu, koszt na końcu.

## Kiedy koniec

Testy ZALICZONE i sprawdzenia ręczne zgodne. Wtedy:

```bash
~/workshop/bin/zakoncz 8
```

## Jeśli utkniesz

Zawołaj prowadzącego.
