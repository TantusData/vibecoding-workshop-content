# OpsCopilot

The internal IT/OT assistant of the Nordfarm Foods plant: answers the shift's questions about
tickets (NordDesk), systems and procedures (Nordwiki). Tomasz started the prototype — the state he
left and his plan are in `HANDOVER_NOTE.md`.

## Commands (terminal, in this folder)

```bash
python -m opscopilot.cli status              # what really works — straight from the code
python -m opscopilot.cli ask "Check ticket INC-1042."
python -m opscopilot.webapp                  # the chat page — open it through the PORTS panel
python -m norddesk_mcp init --force          # reset the NordDesk data to its starting state
```

Do not open the page at a `localhost` address — in your browser that is your laptop, not this
machine. The address is in the **Ports** panel. The page reloads itself after a code change; when
the answers look stale, stop it (`Ctrl+C`) and start it again.

## Where things are

| What | Where |
|---|---|
| The app's look | `opscopilot/webapp/static/theme.css`, `opscopilot/webapp/static/branding.json` |
| Rules for the coding assistant (yours) | `.clinerules/moje-zasady.md` |
| Project context for the coding assistant | `.clinerules/projekt.md` |
| The plan stage in progress (set by `~/workshop/bin/krok`) | `.clinerules/aktualny-etap.md` |
| Application code | `opscopilot/` |
| The company's fake systems (ready) | `norddesk_mcp/` (tickets), `nordwiki_mcp/` (wiki) |
| Data | `data/` — tickets, wiki pages, incident history, test sets |
| Working state (outside git) | `var/` — ticket database, audit log, index, conversation memory |
| Requirements and acceptance tests (read-only) | `~/workshop/specs/`, `~/workshop/tests/` |
