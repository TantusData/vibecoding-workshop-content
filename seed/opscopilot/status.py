"""opscopilot/status.py — what this repo can actually do right now, derived from the code.

Purpose:      The step 01 question ("what works, what is still a TODO?") answered by introspection:
              probes each capability the way a user would hit it (a real MCP call, a retrieval,
              a model file on disk, a scan of a stub's body for NotImplementedError) and reports
              working / stub / missing. Never calls the LLM. `opscopilot status` prints it; the
              universal demo runs it as step 1.
Entry points: capabilities() -> list[Capability], render(caps) -> str, Capability
Depends on:   inspect (stdlib); every subsystem it probes (mcp_tickets, mcp_wiki, rag, govern,
              impact, report)
Used by:      opscopilot.cli (`status`), scripts/demo.py
Invariants:   A probe failure is reported, never raised; the command always prints something.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent


class Capability(BaseModel):
    name: str
    state: str  # working | stub | missing | error
    detail: str


def _is_stub(fn: object) -> bool:
    try:
        return "raise NotImplementedError" in inspect.getsource(fn)  # type: ignore[arg-type]
    except (OSError, TypeError):
        return False


def _probe_tickets() -> Capability:
    from opscopilot.mcp_tickets import client

    stubs = [n for n, f in client.TOOLS.items() if _is_stub(f)]
    if stubs:
        return Capability(
            name="NordDesk tickets (MCP client)", state="stub", detail=f"TODO: {stubs}"
        )
    try:
        rota = client.run(client.get_oncall("day"))
        return Capability(
            name="NordDesk tickets (MCP client)",
            state="working",
            detail=f"{len(client.TOOLS)} tools; live call ok ({len(rota)} day on-call rows)",
        )
    except Exception as err:  # noqa: BLE001 — a status report must not crash
        return Capability(name="NordDesk tickets (MCP client)", state="error", detail=str(err)[:80])


def _probe_wiki() -> Capability:
    from opscopilot.mcp_wiki import client

    if not hasattr(client, "list_pages") or _is_stub(client.list_pages):
        return Capability(name="Nordwiki docs (MCP client)", state="stub", detail="connect() only")
    try:
        pages = client.run(client.list_pages())
        return Capability(
            name="Nordwiki docs (MCP client)", state="working", detail=f"{len(pages)} pages served"
        )
    except Exception as err:  # noqa: BLE001
        return Capability(name="Nordwiki docs (MCP client)", state="error", detail=str(err)[:80])


def _probe_rag() -> Capability:
    from opscopilot.rag import retrieve

    src = inspect.getsource(retrieve.retrieve)
    if src.rstrip().endswith("...") or _is_stub(retrieve.retrieve):
        return Capability(name="Retrieval (RAG)", state="stub", detail="retrieve() has no body")
    try:
        hits = retrieve.retrieve("VPN setup", k=1)
        detail = (
            f"embedder + flat index; top hit for 'VPN setup' = {hits[0].id}"
            if hits
            else "empty index"
        )
        return Capability(name="Retrieval (RAG)", state="working", detail=detail)
    except Exception as err:  # noqa: BLE001
        return Capability(name="Retrieval (RAG)", state="error", detail=str(err)[:80])


def _probe_report() -> Capability:
    if (ROOT / "report.py").exists():
        return Capability(
            name="Handover report", state="working", detail="`report` command, Marek's template"
        )
    if (ROOT / "templates" / "handover.md").exists():
        return Capability(
            name="Handover report", state="stub", detail="Marek's template only, no report.py"
        )
    return Capability(name="Handover report", state="missing", detail="")


def _probe_govern() -> Capability:
    d = ROOT / "govern"
    mods = sorted(p.stem for p in d.glob("*.py") if p.stem != "__init__")
    if not mods:
        return Capability(
            name="Guardrails (govern)", state="stub", detail="empty package, one TODO"
        )
    todo = [m for m in mods if "raise NotImplementedError" in (d / f"{m}.py").read_text("utf-8")]
    if todo:
        return Capability(name="Guardrails (govern)", state="stub", detail=f"TODO: {todo}")
    return Capability(name="Guardrails (govern)", state="working", detail=", ".join(mods))


def _probe_impact() -> Capability:
    if not (ROOT / "impact" / "estimate.py").exists():
        return Capability(name="Impact model", state="stub", detail="no estimate.py yet")
    from opscopilot.impact.train import MODEL_PATH

    if not MODEL_PATH.exists():
        return Capability(
            name="Impact model", state="working", detail="trained on first use (about a second)"
        )
    size_kb = MODEL_PATH.stat().st_size // 1024
    return Capability(
        name="Impact model", state="working", detail=f"{MODEL_PATH.name} ({size_kb} kB)"
    )


def _probe_llm() -> Capability:
    from opscopilot.llm.client import get_llm_client

    c = get_llm_client()
    return Capability(name="LLM (model gateway)", state="working", detail=f"provider={c.provider}")


def capabilities() -> list[Capability]:
    return [
        _probe_llm(),
        _probe_tickets(),
        _probe_wiki(),
        _probe_rag(),
        _probe_report(),
        _probe_govern(),
        _probe_impact(),
    ]


def render(caps: list[Capability]) -> str:
    width = max(len(c.name) for c in caps)
    lines = [f"{c.name:{width}s}  {c.state:8s} {c.detail}" for c in caps]
    todo = [c.name for c in caps if c.state != "working"]
    lines.append("")
    lines.append("still TODO: " + (", ".join(todo) if todo else "nothing — every module is wired"))
    return "\n".join(lines)
