"""Step 01 — the project is yours: its look, its texts, your rules for the agent.

The look lives in exactly two files (theme.css, branding.json) that a catch-up never overwrites
once you changed them; the page itself keeps every URL relative, because on the course
machines the app is served under /proxy/8000/. Your rules for the agent live in
.clinerules/moje-zasady.md."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

WS = Path(__file__).resolve().parent.parent.parent
SEED = WS / "seed"
STATIC = Path("opscopilot/webapp/static")
BRANDING_KEYS = ("name", "tagline", "welcome", "placeholder")


def test_branding_json_is_valid_and_has_every_text():
    data = json.loads((STATIC / "branding.json").read_text(encoding="utf-8"))
    for key in BRANDING_KEYS:
        assert isinstance(data.get(key), str) and data[key].strip(), f"branding.json: '{key}'"


def test_branding_json_is_yours():
    mine = json.loads((STATIC / "branding.json").read_text(encoding="utf-8"))
    seed = json.loads((SEED / STATIC / "branding.json").read_text(encoding="utf-8"))
    assert mine != seed, "branding.json is still the seed version — give the app your own texts"


def test_theme_css_is_yours_and_well_formed():
    css = (STATIC / "theme.css").read_text(encoding="utf-8")
    assert css != (SEED / STATIC / "theme.css").read_text(encoding="utf-8"), (
        "theme.css is still the seed version — change the colours/fonts"
    )
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert body.count("{") == body.count("}"), "theme.css: unbalanced { }"
    assert "--accent" in body, "theme.css: keep the variables (at least --accent) for app.css"


def test_every_url_on_the_page_is_relative():
    """Served under /proxy/8000/: a URL starting with "/" escapes that prefix and 404s."""
    absolute = re.compile(r"""(href|src|action)\s*=\s*["']/|fetch\(\s*["'`]/|url\(\s*["']?/""")
    for name in ("index.html", "app.css", "theme.css"):
        text = (STATIC / name).read_text(encoding="utf-8")
        hits = [m.group(0) for m in absolute.finditer(text)]
        assert not hits, f"{name}: absolute URL(s) {hits} — use relative ones (no leading /)"


def test_the_page_is_served_with_your_files():
    from fastapi.testclient import TestClient

    from opscopilot.webapp.app import app

    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "static/theme.css" in page.text and "static/branding.json" in page.text
        assert client.get("/static/theme.css").status_code == 200
        assert client.get("/static/branding.json").json()["name"]


def test_you_wrote_rules_for_the_agent():
    path = Path(".clinerules/moje-zasady.md")
    assert path.exists(), ".clinerules/moje-zasady.md is missing"
    text = path.read_text(encoding="utf-8")
    assert text != (SEED / path).read_text(encoding="utf-8"), "moje-zasady.md: add your rules"
    rules = [ln for ln in text.splitlines() if re.match(r"\s*(-|\*|\d+[.)])\s+\S", ln)]
    assert len(rules) >= 3, f"moje-zasady.md: at least 3 rules as list items, found {len(rules)}"


def test_the_project_is_under_version_control():
    assert Path(".git").exists(), "the project folder must be a git repository"
    assert os.system("git rev-parse --verify -q HEAD >/dev/null 2>&1") == 0, "no commit yet"
