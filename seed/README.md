# OpsCopilot

Wewnętrzny asystent IT/OT zakładu Nordfarm Foods: odpowiada zmianie na pytania o zgłoszenia
(NordDesk), systemy i procedury (Nordwiki). Prototyp zaczął Tomasz — stan zastany i jego plan są
w `HANDOVER_NOTE.md`.

## Polecenia (terminal, w tym katalogu)

```bash
python -m opscopilot.cli status              # co naprawdę działa — prosto z kodu
python -m opscopilot.cli ask "Sprawdź zgłoszenie INC-1042."
python -m opscopilot.webapp                  # strona czatu — otwórz ją przez panel PORTS
python -m norddesk_mcp init --force          # przywróć dane NordDesk do stanu wyjściowego
```

Strony nie otwieraj pod adresem `localhost` — w Twojej przeglądarce to Twój laptop, nie ta
maszyna. Adres jest w panelu **Ports**. Strona przeładowuje się sama po zmianie kodu; gdy
odpowiedzi wyglądają na stare, zatrzymaj ją (`Ctrl+C`) i uruchom ponownie.

## Gdzie co jest

| Co | Gdzie |
|---|---|
| Wygląd aplikacji | `opscopilot/webapp/static/theme.css`, `opscopilot/webapp/static/branding.json` |
| Zasady dla asystenta kodu (Twoje) | `.clinerules/moje-zasady.md` |
| Kontekst projektu dla asystenta kodu | `.clinerules/projekt.md` |
| Etap planu w toku (ustawia go `~/workshop/bin/krok`) | `.clinerules/aktualny-etap.md` |
| Kod aplikacji | `opscopilot/` |
| Udawane systemy firmy (gotowe) | `norddesk_mcp/` (zgłoszenia), `nordwiki_mcp/` (wiki) |
| Dane | `data/` — zgłoszenia, strony wiki, historia incydentów, zestawy testowe |
| Stan w trakcie pracy (poza git) | `var/` — baza zgłoszeń, dziennik audytu, indeks, pamięć rozmów |
| Wymagania i testy odbiorcze (tylko do odczytu) | `~/workshop/specs/`, `~/workshop/tests/` |
