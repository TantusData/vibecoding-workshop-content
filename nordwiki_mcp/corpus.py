"""nordwiki_mcp/corpus.py — the fake Nordwiki's data: a folder of markdown pages, re-read per call.

Purpose:      Treats every `*.md` under wiki_root() (NORDWIKI_ROOT, default data/wiki) as one
              page. Nothing is indexed or cached: each call walks the folder again, so a page
              edited on disk is live on the next call. Search is a deliberately naive keyword
              count — good enough to find a page by title words, bad enough that proper retrieval
              (rag/) is worth building.
Entry points: list_pages(), get_page(), search_pages(), page_id(), wiki_root()
Depends on:   stdlib only (pathlib, re, os)
Used by:      nordwiki_mcp.server (wraps these as MCP tools), nordwiki_mcp.__main__ (init check)
Invariants:   Read-only — nothing here ever writes to the wiki folder. Page id == file stem, exactly
              (spaces and parentheses included), so ids round-trip to files without a lookup table.
              `_ground_truth.csv` and other non-`.md` files are never served.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WIKI_ROOT = REPO_ROOT / "data" / "wiki"


def wiki_root() -> Path:
    """Resolved on every call so NORDWIKI_ROOT can point a test at another folder."""
    return Path(os.environ.get("NORDWIKI_ROOT", DEFAULT_WIKI_ROOT))


_WORD = re.compile(r"[a-z0-9][a-z0-9\-]+")


def page_id(path: Path) -> str:
    return path.stem


def _pages() -> list[Path]:
    """Every markdown page, sorted by name, discovered fresh on each call."""
    root = wiki_root()
    if not root.exists():
        raise FileNotFoundError(f"{root} not found — is NORDWIKI_ROOT set correctly?")
    return sorted(p for p in root.rglob("*.md") if not p.name.startswith("_"))


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _meta(path: Path, text: str) -> dict[str, Any]:
    return {
        "id": page_id(path),
        "title": _title(text, path.stem),
        "path": str(path.relative_to(wiki_root())),
        "words": len(text.split()),
    }


def list_pages() -> list[dict[str, Any]]:
    return [_meta(p, p.read_text(encoding="utf-8")) for p in _pages()]


def get_page(page_id_: str) -> dict[str, Any]:
    """Full page by id (the file stem). Unknown id -> {"error": ...}."""
    for p in _pages():
        if page_id(p) == page_id_:
            text = p.read_text(encoding="utf-8")
            return {**_meta(p, text), "content": text}
    return {"error": f"page {page_id_!r} not found"}


def search_pages(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Rank pages by how many times the query's words occur (title hits count triple)."""
    terms = [t for t in _WORD.findall(query.lower()) if len(t) > 2]
    if not terms:
        return []
    scored = []
    for p in _pages():
        text = p.read_text(encoding="utf-8")
        low = text.lower()
        title = _title(text, p.stem).lower()
        score = sum(low.count(t) + 3 * title.count(t) for t in terms)
        if score:
            snippet_at = min((low.find(t) for t in terms if t in low), default=0)
            snippet = text[max(0, snippet_at - 80) : snippet_at + 200].replace("\n", " ")
            scored.append({**_meta(p, text), "score": score, "snippet": snippet.strip()})
    scored.sort(key=lambda r: (-r["score"], r["id"]))
    return scored[: max(1, limit)]
