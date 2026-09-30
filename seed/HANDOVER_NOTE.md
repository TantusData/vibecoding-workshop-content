# Handover — the OpsCopilot prototype

Hi, Tomasz here — the contractor this all started with. The contract ended before the project was
ready; sorry for handing over something half-done. Here is where things stand.

## What already works

- The model connection (`opscopilot/llm/client.py`) — through the company's LiteLLM gateway, model
  `bedrock-claude`, key from the environment variable `LITELLM_VIRTUAL_KEY` (already set on our
  machines). Structured answers (JSON by schema) are done and tested. This part is solid — build
  on it, do not rewrite it. `LLM_PROVIDER=fake` gives a deterministic stand-in for tests.
- `python -m opscopilot.cli ask "..."` — works end to end, but it is only a raw question to the
  model. No knowledge of our systems, no documentation. Asked which VPN address to use or how to
  restart the packing line's MES — it will make something up with full confidence. Asked about a
  ticket number — it will say it cannot see NordDesk.
- A simple chat page (`opscopilot/webapp/`, `python -m opscopilot.webapp`) that calls the same
  `ask()`. Ugly, but it works. `python -m opscopilot.cli status` says what really works —
  straight from the code.
- Both fake systems: `norddesk_mcp/` (tickets, a JSON file) and `nordwiki_mcp/` (documentation, a
  folder of markdown files in `data/wiki/`) are working MCP servers. They read their files on
  every call, so the data can be changed while you work. The NordDesk data is from the day of the
  palletiser breakdown (INC-1042, 11 September 2026) — I left it like that so there is something
  to work with.
- Things you do not need to write: the data models (`schema.py`), the SQLite store (`store.py`),
  embeddings handling (`rag/embed.py` — also through the gateway, model `titan-embed`), the MCP
  client for the wiki (`mcp_wiki/client.py`).
- My side project, `opscopilot/impact/` — estimating downtime and cost in EUR: a scikit-learn
  regressor trained on the incident history in `data/incidents/` (the model trains itself on first
  use, about a second). `python -m opscopilot.cli impact INC-1042` shows the result and the
  factors that moved it; `python scripts/train_impact.py --variant leaked --eval` shows what bad
  data does to R². No LLM at all. Note: that command reads `var/norddesk.json` directly, not
  through the MCP client (which does not exist) — fine for a side project, not for the app.

## What I started and did not finish

- `opscopilot/mcp_tickets/` — the MCP client for NordDesk. The connection and the function
  signatures are there, but every function is `NotImplementedError("TODO")`. This is the first
  thing to do — without it nothing else makes sense. HTTP calls are made with `httpx`.
- `opscopilot/history.py` — conversation memory. The store is there, the conversation-window
  logic is not.
- `opscopilot/loop.py` — several tools for one question. Signatures only.

## What I did not get to

- `opscopilot/govern/` — empty functions. This worries me most: before anyone outside IT touches
  it, the assistant must refuse what it should not answer and must not be talked into leaking
  data.
- `opscopilot/rag/` — wiki search. The embeddings are there; splitting into chunks, the index and
  `retrieve()` — not.
- Marek (the shift manager) wants an automatic summary at the end of a shift in a specific format.
  His template is in `opscopilot/templates/handover.md`; zero implementation.

## Plan — if I were staying (or for whoever takes this over)

1. Takeover: read this note and check it against the code, set up your coding assistant (Cline)
   for yourself in `.clinerules/moje-zasady.md`, give the chat page the Nordfarm look
2. The MCP client for tickets (without it nothing works)
3. Conversation memory (and see what it breaks)
4. The tool loop
5. Decide what the assistant must refuse — before any blocking is built
6. Guardrails
7. Wiki search (RAG)
8. Polish — answer trace and costs, Marek's report, the impact estimate as an assistant tool

Good luck. — T.
