# Etap 1 z planu Tomasza — Przejęcie projektu: notatka Tomasza a kod

## Decyzje

- Najpierw kontekst, potem kod: agent dostaje trwały kontekst projektu w katalogu `.clinerules/`
  (czyta go przy każdym zadaniu). Zasady właściciela projektu — w `.clinerules/moje-zasady.md`.
- Gdy notatka i kod się nie zgadzają, faktem jest kod.
- Wygląd aplikacji to **dokładnie dwa pliki**: `opscopilot/webapp/static/theme.css` (kolory,
  czcionki, dowolne reguły CSS) i `opscopilot/webapp/static/branding.json` (nazwa, podtytuł,
  logo, powitanie, podpowiedź). O wyglądzie decyduje właściciel projektu.
- Każdy adres na stronie zostaje względny (aplikacja działa pod `/proxy/8000/`).

## Czego nie robimy

- Nie przepisujemy tego, co Tomasz zrobił i co działa.
- Nie zmieniamy `index.html` ani `app.css` dla wyglądu (należą do aplikacji).
- Nie „naprawiamy" danych w `data/` — część jest celowo taka, jaka jest, i tak ma zostać.

## Etap 1 — kontrakt: przejęcie projektu

W tym etapie nie zmienia się logika aplikacji. Ustalone jest:

## Wygląd to dokładnie dwa pliki

| Plik | Czyj | Co w nim jest |
|---|---|---|
| `opscopilot/webapp/static/theme.css` | **właściciela projektu** | zmienne CSS (`--bg`, `--panel`, `--ink`, `--muted`, `--line`, `--bubble`, `--accent`, `--accent-ink`, `--font`, `--size`, `--radius`, …) i dowolne dodatkowe reguły CSS. Ładowany **po** `app.css`, więc jego reguły wygrywają. Zmienna `--accent` musi zostać. |
| `opscopilot/webapp/static/branding.json` | **właściciela projektu** | `{"name", "tagline", "logo", "welcome", "placeholder"}` — same napisy; `logo` może być puste albo emoji. Strona czyta go przy ładowaniu; zepsuty plik = teksty domyślne. |
| `opscopilot/webapp/static/index.html`, `app.css` | aplikacji | struktura i układ. **Nie zmieniać ich dla wyglądu.** |

O obu plikach decyduje właściciel projektu: kolory, teksty i ton wybiera on, nie agent.

## Każdy adres jest względny

Na naszych maszynach aplikacja działa pod `/proxy/8000/`. `href="static/app.css"`, `fetch('ask')` —
nigdy `"/static/…"` ani `fetch('/ask')`: początkowy `/` wychodzi poza prefiks i kończy się 404.
To samo dotyczy `url(/…)` w CSS.

## Zasady dla agenta

`.clinerules/moje-zasady.md` — co najmniej trzy zasady jako punkty listy (`- …` albo `1. …`).
Pisze je właściciel projektu, nie agent. Agent czyta każdy plik w `.clinerules/` na początku
każdego zadania: `projekt.md` to kontekst projektu, `aktualny-etap.md` wskazuje etap w toku.

## Polecenia

- `python -m opscopilot.cli status` / `ask "…"` / `impact INC-1042`
- `python -m opscopilot.webapp` — strona czatu na porcie 8000 (otwierana z panelu Ports)
- `python scripts/train_impact.py --variant clean|shuffled|leaked --eval`

## Testy

`~/workshop/tests/01/` — `test_your_project.py` (wygląd jest Twój, adresy względne, trzy zasady,
projekt jest repozytorium git) oraz testy jednostkowe tego, co już działa (`unit/`: klient
modelu, magazyny, klient wiki, model wpływu, dziennik audytu).

## Sprawdzanie

Po każdej zmianie: `~/workshop/bin/sprawdz 1`. Etap kończy właściciel projektu — po swoich sprawdzeniach ręcznych.
