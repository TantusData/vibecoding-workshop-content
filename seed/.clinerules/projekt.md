# Project: OpsCopilot (context for the agent)

You are helping to finish an inherited prototype: **OpsCopilot**, the internal IT/OT assistant of
the Nordfarm Foods plant. The contractor Tomasz started it; his contract ended before the project
was ready. The state he left is described in his note `HANDOVER_NOTE.md` — with one caveat: when
the note and the code disagree, the code is the fact. The data in NordDesk is from 11 September
2026 (the day of the INC-1042 breakdown) — treat it as current.

## The plan and the stage in progress

- We finish the project following Tomasz's plan (`HANDOVER_NOTE.md`, section "Plan"), stage by
  stage.
- The stage in progress, its requirements and acceptance tests are named in
  `.clinerules/aktualny-etap.md`. If it is missing, ask which stage you are working on.
- The requirements files (`~/workshop/specs/`) are written in Polish; read them as they are. Talk
  to the person you work with in English unless they write otherwise.
- When asked about the state of the project: describe what the application can and cannot do —
  from the code, `python -m opscopilot.cli status` and Tomasz's note. Do not describe the way of
  working, the stages or what comes later.

## Where you may work

- Code and every change: **only** this folder, `~/work/project`.
- `~/workshop` is the acceptance pack (requirements, contracts, acceptance tests, commands) —
  **read-only**. A changed acceptance test does not complete a stage.
- **Do not read `~/workshop/steps/`, `~/workshop/README.md`, `~/workshop/GUIDE_EN.md` or
  `~/workshop/CHEATSHEET_EN.md`** — they are the notes of the person you work with, not your tasks. Your requirements are in
  `~/workshop/specs/`.
- Change the app's look **only** in `opscopilot/webapp/static/theme.css` (colours, fonts, any CSS
  rules) and `opscopilot/webapp/static/branding.json` (texts). `index.html` and `app.css` belong
  to the application.
- Every URL on the page must be **relative** (`static/app.css`, `ask`) — never starting with `/`.
  The app runs under `/proxy/8000/`.
- Do not change the data in `data/` — some of it is deliberately the way it is.
- Do not add dependencies and do not run `pip install` — the packages on this machine are fixed.

## How we work

- Read only the files the task needs — do not browse whole folders "just in case".
- **Tool test first, then agent test.** The tests in `~/workshop/tests/NN/unit/` (the tool alone,
  fixed input, exact result) must be green before you turn to `~/workshop/tests/NN/agent/`
  (whether the assistant uses the tool correctly).
- After every change run the check command from `aktualny-etap.md` and read the names of the red
  tests — they say what is missing. The command runs without a model and costs nothing.
- A file with a `# CONTRACT` banner has fixed signatures, docstrings, dataclasses and constants —
  do not change their names or shape; you fill in function bodies and empty pattern lists.
- When you change a function, fix its description too (docstring, file header) if it stopped
  being true.
- The chat page (`python -m opscopilot.webapp`) reloads itself after a code change. It is opened
  through the Ports panel — never give a `localhost` address as a link to open.
- When the conversation takes more than half of the context window, suggest moving to a new task
  (`new_task`) with a summary: the stage, what is done, what is left, the last test result.

## Never

- **Do not perform the manual checks and never write that they passed.** The person you work with
  does them. Automated tests do not replace them — they can be green while the app is broken.
- **Do not decide for the person what they are meant to judge themselves**: whether Tomasz's note
  is true, whether a result can be trusted, which decision to take. Ask what they think; you may
  help check the evidence.
- **Do not write for them** their rules (`.clinerules/moje-zasady.md`), their decisions about the
  look, or the content of the stage 5 decision set. You may give examples when asked.
- **Do not write a plan when you do not know the goal and the decisions** — ask for them (goal,
  what not to touch, order) instead of inventing them.
- **Do not write that a stage is finished.** The person finishes it with `~/workshop/bin/zakoncz`.
- **Do not run commands that call the real model** (`python -m opscopilot.cli ask`, the chat
  page) without an explicit request — each one costs money.
- **Do not run** `~/workshop/bin/krok`, `~/workshop/bin/zakoncz`, `~/workshop/bin/checkpoint` or
  `~/workshop/bin/undo` — those are the decisions of the person you work with. For clarity:
  `zakoncz N` saves the project (commit) after their confirmation; `checkpoint N` replaces the code
  with the finished state after stage N (`undo` reverses it).

## Limits of the assistant we are building

- **Writing needs a human.** `create_ticket` and `post_update` change NordDesk — they go through
  the approval gate.
- **Never touch a controller (PLC), a line or anything outside NordDesk/Nordwiki** — there is no
  tool for it and there will not be one.
