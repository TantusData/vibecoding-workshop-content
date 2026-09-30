# Cheat-sheet — terminal commands

Type every command in the code-server terminal (menu → Terminal → New Terminal). A new terminal
starts in `~/work/project`. The `python -m opscopilot…` commands work only in that folder — when
in doubt, first: `cd ~/work/project`.

## Course steps

| I want to… | Command |
|---|---|
| start step N | `~/workshop/bin/krok N` (parts B: `krok 3b`, `krok 7b`) |
| check whether the tests pass | `~/workshop/bin/sprawdz N` (parts: `3a`, `3b`, `7a`, `7b`) |
| finish a step (manual checks + save) | `~/workshop/bin/zakoncz N` — answer each question `y` or `n` |
| catch up — the finished state after step N | `~/workshop/bin/checkpoint N` — confirm by typing `YES` |
| undo the last checkpoint | `~/workshop/bin/undo` — confirm by typing `YES` |
| restore the course materials when `sprawdz` says "STOP" | `~/workshop/bin/sprawdz przywroc` |

A command without a number (e.g. `~/workshop/bin/krok`) prints how to use it.

## The app

| I want to… | Command | From step |
|---|---|---|
| see what the app can really do | `python -m opscopilot.cli status` | 01 |
| ask a question | `python -m opscopilot.cli ask "Check ticket INC-1042."` | 01 |
| start the chat page | `python -m opscopilot.webapp`, then the **Ports** panel → port 8000 | 01 |
| stop the chat page | `Ctrl+C` in its terminal | 01 |
| downtime and cost estimate (Tomasz's ML model) | `python -m opscopilot.cli impact INC-1042` | 01 |
| reset the NordDesk data to its starting state | `python -m norddesk_mcp init --force` | 01 |
| ask within one named conversation | `python -m opscopilot.cli ask --session demo "…"` | 03 |
| start a new conversation | `python -m opscopilot.cli ask --new "…"` or `python -m opscopilot.cli history new` | 03 |
| see what the assistant remembers | `python -m opscopilot.cli history show --session demo` | 03 |
| see an answer's trace (tools, cost) | `python -m opscopilot.cli ask --trace "…"` | 08 |
| model call costs | `python -m opscopilot.cli usage` | 08 |
| end-of-shift report | `python -m opscopilot.cli report --shift day` | 08 |

Questions to the app (`ask`, the chat page) cost money — each is a model call. The
`~/workshop/bin/…` commands are free: they run without a model.

## Is my work saved?

| I want to… | Command |
|---|---|
| the project's latest saves | `git -C ~/work/project log --oneline -5` |
| what changed since the last save | `git -C ~/work/project status` |
| which steps are finished | `cat ~/work/project/.git/workshop-done` |
| backup branches after `undo` | `git -C ~/work/project branch` (names `zapas/…` = backup/…) |

The project is saved automatically by `zakoncz` and before every `checkpoint`. A machine restart
deletes nothing in `~/work/project`.

## When something does not work

| Symptom | What to do |
|---|---|
| "Python on this machine is still installing" | Wait a minute after the machine starts. Ready when `ls /opt/venv/.ready` shows no error. |
| The connection dropped while Cline was working | Reload the page (F5) → Cline panel → **Resume Task**. |
| Cline does not respond, the panel "hangs" | `Ctrl+Shift+P` → **Developer: Restart Extension Host** (files and conversation stay), then **Resume Task**. |
| The chat page does not open | Is `python -m opscopilot.webapp` running in some terminal? Use the address from the **Ports** panel only, never `localhost`. |
| "address already in use" when starting the page | The page is already running in another terminal — `Ctrl+C` there. Or: `pkill -f opscopilot.webapp` and start it again. |
| The page shows stale answers | `Ctrl+C` in the page's terminal, then `python -m opscopilot.webapp`. |
| `No module named opscopilot` | The terminal is in the wrong folder: `cd ~/work/project`. |
| `sprawdz` says "STOP: someone changed the course materials" | `~/workshop/bin/sprawdz przywroc`, then `sprawdz` again. We change only `~/work/project`. |
| Something disappeared after `checkpoint` | `~/workshop/bin/undo` — the state before the checkpoint comes back. |
| NordDesk data mixed up after experiments | `python -m norddesk_mcp init --force` |
| The machine restarted and the terminal speaks Polish again | Tell the person who set up your machine — the English version has to be set up again (your work in `~/work/project` is safe). |
| None of this helps | Ask the person who set up your machine. Do not install packages (`pip install`) and do not change `~/workshop`. |
