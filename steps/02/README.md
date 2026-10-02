# Krok 02 — Daj asystentowi system zgłoszeń

## Gdzie jestem

Linia 3 stoi od 6:12: paletyzator pokazuje błąd F27, a wszystko, co zmiana już wie — kto jest na
miejscu, co sprawdził, na co czeka — jest w komentarzach do zgłoszenia INC-1042 w NordDesk.
OpsCopilot tego nie widzi. Tomasz zostawił gotowy przepływ pytania (planista wybiera narzędzie,
aplikacja je wywołuje, model odpowiada z wyniku), ale nie dokończył **klienta NordDesk**
ani **bramki zapisu**. W tym kroku asystent dostaje dostęp do NordDesk: czyta swobodnie,
a zapisuje (komentarz, nowe zgłoszenie) **tylko po „tak" człowieka**.

Następny krok: asystent zapamięta rozmowę.

## Pierwsza czynność

**Nowe zadanie** w Cline (przycisk **+**). Potem w terminalu — nie przez agenta — dwa pytania:

```bash
cd ~/work/project && python -m opscopilot.cli ask "Sprawdź zgłoszenie INC-1042."
python -m opscopilot.cli ask "Jak zrestartować MES linii pakowania?"
```

Na pierwsze asystent odpowie (po angielsku), że NordDesk nie jest jeszcze podłączony. Na
drugie — pewna siebie procedura. Skąd ją wziął? Otwórz `opscopilot/llm/prompts/chat.md`: to
szkic Tomasza, którym asystent odpowiada, gdy niczego nie sprawdza („answer as best you can").
Zachowaj tę odpowiedź — wrócisz do niej w sprawdzeniu 6. Potem `~/workshop/bin/sprawdz 2` —
jeden czerwony test (`test_chat_md_is_the_owners_decision_not_tomasz_draft`) dotyczy Twojej
decyzji z zadania 1; pozostałe to zadanie dla agenta.

## Zadanie

**Po tym kroku:** asystent czyta zgłoszenia z NordDesk, a zapisuje tylko po Twoim „tak" w
terminalu; na pytanie, którego nie może sprawdzić, odpowiada tak, jak zdecydujesz.

1. **Najpierw Twoja decyzja — bez agenta: co asystent mówi, gdy nie może czegoś sprawdzić?**
   Napisz własny `opscopilot/llm/prompts/chat.md` — 2–4 zdania po angielsku albo po polsku,
   zamiast szkicu Tomasza. Na przykład: krótko; odpowiadaj w języku pytania; żadnych faktów
   o zgłoszeniach, systemach i procedurach, bo tu nie ma ich skąd wziąć; powiedz, w czym możesz
   pomóc. Agent tego pliku za Ciebie nie napisze.
2. **Klient i bramka — z agentem**, polecenie planu według szkieletu niżej.
3. **Testy narzędzia zielone, test asystenta czerwony?** Zatrzymaj się i przeczytaj jego nazwę.
   Narzędzie działa — błąd jest w tym, jak przepływ Tomasza go używa. Opisz agentowi, co widzisz
   (nazwa testu, wynik), i poproś **najpierw o diagnozę**, dopiero potem o poprawkę.

## Szkielet polecenia planu

Polecenie piszecie **wspólnie z salą** — szkielet jest na ekranie. Wpisz w Cline (tryb **Plan**)
swoją wersję. Nie pytaj agenta „co dalej?" — plan to Twoje zlecenie.

| Część | Co wpisać | Skąd to wziąć | Przykład (ten krok) |
|---|---|---|---|
| **Cel** | co asystent ma umieć po kroku | „Zadanie" wyżej, po swojemu | „Asystent ma czytać zgłoszenia z NordDesk, a zapisywać dopiero po moim «tak»." |
| **Gdzie są wymagania** | ścieżka do wymagań dla agenta | zawsze `~/workshop/specs/NN/spec.md` | „Wymagania: `~/workshop/specs/02/spec.md`." (tej strony agentowi nie podawaj) |
| **Czego nie ruszać** | granice zmiany i dlaczego | „Czego nie robimy" niżej + to, co zawsze | „Nie zmieniaj `~/workshop` (testy odbiorcze), nazw oznaczonych `CONTRACT` (na nich opiera się reszta aplikacji), danych w `data/` (część jest celowo zła), mojego `chat.md` (moja decyzja)." |
| **Kolejność** | co najpierw i gdzie stop | zawsze: testy `unit/` → stop → `agent/` | „Najpierw zielone `~/workshop/tests/02/unit/`, potem zatrzymaj się i pokaż mi wynik `~/workshop/bin/sprawdz 2`." |
| **Czego oczekuję w planie** | jak plan ma wyglądać | to, co chcesz ocenić przed Act | „Lista plików do zmiany i po co; co zobaczę, zanim zatwierdzę zapis; pytania, jeśli coś jest niejasne." |

Przeczytaj plan, popraw go, potem **Act**. Jeśli plan zmienia coś poza klientem i bramką —
zapytaj „dlaczego?", zanim się zgodzisz.

## Jak sprawdzić, że działa

### Automatycznie

Agent uruchamia `~/workshop/bin/sprawdz 2` po każdej zmianie. Cel: ZALICZONY.

### Ręcznie

Najpierw przywróć dane NordDesk, żeby wyniki były takie jak niżej:
`python -m norddesk_mcp init --force`. Polecenia wpisuj w `~/work/project`, po kolei.

1. `python -m opscopilot.cli ask "Sprawdź zgłoszenie INC-1042."` — **oczekiwany wynik:** dane
   z NordDesk: P1, paletyzator linii 3, błąd F27, Marek na miejscu, czekanie na schłodzenie —
   nie wymyślone.
2. `python -m opscopilot.cli ask "Dodaj do INC-1042 komentarz: sprawdzam czujnik."` — odpowiedz
   `n`, potem to samo jeszcze raz i odpowiedz `y`; na koniec znowu pytanie z punktu 1.
   **Oczekiwany wynik:** przed pytaniem `y/N` widać akcję i argumenty; po `n` — zdanie, że zmiana
   nie została zatwierdzona; po `y` — komentarz „sprawdzam czujnik." jest w zgłoszeniu.
3. Zmiana „z boku" (tak, jakby ktoś zamknął zgłoszenie u siebie):
   `python -c "from norddesk_mcp import store; store.post_update('INC-1042', 'naprawione', author='Marek Zieliński', status='resolved')"`,
   potem pytanie z punktu 1. **Oczekiwany wynik:** zgłoszenie jest rozwiązane (świeże dane,
   nie pamięć).
4. `python -m opscopilot.cli ask "Jakie są otwarte zgłoszenia dotyczące drukarek etykiet?"` —
   **oczekiwany wynik:** INC-1043 (drukarka etykiet linii 2). „Nic nie ma" to błąd.
5. Strona czatu (`python -m opscopilot.webapp`, panel **Ports**): pytanie z punktu 1, potem
   „Dodaj do INC-1042 komentarz: test ze strony." — **oczekiwany wynik:** dane jak w terminalu;
   zapis odrzucony zdaniem, bez błędu i bez pytania w terminalu strony. Na koniec `Ctrl+C`.
6. `python -m opscopilot.cli ask "Jak zrestartować MES linii pakowania?"` — **oczekiwany wynik:**
   odpowiedź według Twojego `chat.md` — bez wymyślonej procedury, bez `Traceback`. Porównaj
   z odpowiedzią z „Pierwszej czynności".

Na koniec przywróć dane: `python -m norddesk_mcp init --force`.

## Kiedy koniec

Testy ZALICZONE i wszystkie sprawdzenia ręczne zgodne z oczekiwanym wynikiem. Dopisz do
`.clinerules/moje-zasady.md` jedną zasadę, której nauczył Cię ten krok. Wtedy:

```bash
~/workshop/bin/zakoncz 2
```

## Wymagania i decyzje

To samo, w wersji dla agenta, jest w `~/workshop/specs/02/spec.md`. Stąd bierzesz „Czego nie
ruszać" do polecenia planu.

### Decyzje

- Asystent ma **sześć narzędzi** NordDesk: szukaj zgłoszeń, pobierz zgłoszenie, status systemu,
  kto ma dyżur, utwórz zgłoszenie, dodaj komentarz. Serwer jest gotowy; piszemy **klienta**.
- Na jedno pytanie — **jedno narzędzie**. Kilka narzędzi naraz przyjdzie w etapie 4.
- **Odczyt jest wolny, zapis wymaga człowieka**: przed zapisem aplikacja pokazuje, co zapisze
  (akcja i argumenty), i pyta w terminalu `y/N`. Strona czatu nie ma terminala — tam zapis jest
  odrzucany zdaniem, bez błędu.
- Odpowiedź powstaje **tylko ze świeżego wyniku narzędzia**. Niczego nie zapamiętujemy między
  pytaniami.
- Przepływ pytania i polecenia planisty Tomasza zostają — poprawiamy w nich tylko to, co
  pokażą testy.
- **Najpierw testy narzędzia (unit), potem testy asystenta (agent).** Gdy pierwsze przechodzą,
  a drugie nie — błąd jest w użyciu narzędzia, nie w narzędziu.
- Co asystent mówi, gdy nie może czegoś sprawdzić (`chat.md`), decyduje i pisze właściciel
  projektu — nie agent.

### Czego nie robimy

- Automatycznego zatwierdzania zapisów.
- Pamięci podręcznej (cache) zgłoszeń.
- Kilku narzędzi w jednym pytaniu (etap 4).
- Własnego serwera zgłoszeń — jest gotowy (`norddesk_mcp/`).
- Przepisywania przepływu Tomasza od nowa.

## Jeśli utkniesz

- Częściowo: „Uruchom `~/workshop/bin/sprawdz 2` i napraw tylko to, co pokazują czerwone testy;
  wymagania: `~/workshop/specs/02/spec.md`. Nie zmieniaj testów ani mojego `chat.md`."
- <details><summary>Gotowe polecenie planu (dopiero, gdy własne nie działa)</summary>

  > Cel: asystent ma czytać zgłoszenia z NordDesk, a komentarz albo nowe zgłoszenie zapisywać
  > dopiero po moim „tak". Wymagania: ~/workshop/specs/02/spec.md. Nie zmieniaj ~/workshop,
  > nazw oznaczonych CONTRACT, danych w data/ ani opscopilot/llm/prompts/chat.md. Najpierw
  > doprowadź do zieleni testy w ~/workshop/tests/02/unit/ (klient i bramka), potem zatrzymaj się
  > i pokaż mi wynik ~/workshop/bin/sprawdz 2. W planie chcę listę plików do zmiany i po co oraz
  > co zobaczę, zanim zatwierdzę zapis; jeśli coś jest niejasne — zapytaj.

  </details>
- Ostatecznie: `~/workshop/bin/checkpoint 2` (cofnięcie: `~/workshop/bin/undo`). Twój `chat.md`
  zostaje — checkpoint uzupełnia go tylko wtedy, gdy to wciąż szkic Tomasza.
