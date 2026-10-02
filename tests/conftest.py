"""Workshop test harness: the tests live in ~/workshop/tests, the code under test in the
participant's project (OPSCOPILOT_PROJECT, default ~/work/project).

Run through ~/workshop/bin/sprawdz N, which passes only the directories 01…N and sets
WORKSHOP_STEP=N. A few single tests belong to a later step than their file (a
`pytest.mark.step(k)` marker); those are skipped until WORKSHOP_STEP reaches k. Providers are
always fake: no model call, no embedding call, no cost."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PROJECT = Path(os.environ.get("OPSCOPILOT_PROJECT", Path.home() / "work" / "project")).resolve()

sys.path.insert(0, str(PROJECT))  # `import opscopilot` = the participant's code
sys.path.insert(0, str(HERE))  # `import helpers` = the scripted fake model
os.chdir(PROJECT)  # tests read data/ and scripts/ relative to the project

os.environ["LLM_PROVIDER"] = "fake"
os.environ["EMBEDDINGS_BACKEND"] = "fake"
os.environ.setdefault("OPSCOPILOT_AUTO_APPROVE", "1")
os.environ.setdefault("PYTHONHASHSEED", "0")
os.environ["FAKE_LLM_RESPONSES"] = str(HERE / "fixtures" / "llm_responses.json")

_TMP = Path(tempfile.mkdtemp(prefix="opscopilot-tests-"))
os.environ.setdefault("OPSCOPILOT_DB", str(_TMP / "opscopilot.db"))
os.environ.setdefault("OPSCOPILOT_AUDIT_LOG", str(_TMP / "audit.log"))
os.environ.setdefault("OPSCOPILOT_SESSION", "pytest")
os.environ.setdefault("RAG_INDEX_DIR", str(_TMP / "wiki_index"))
os.environ.setdefault("OPSCOPILOT_IMPACT_MODEL", str(_TMP / "impact_model.joblib"))

STEP = int(os.environ.get("WORKSHOP_STEP", "99"))


@pytest.fixture(autouse=True)
def _own_conversation_db(tmp_path, monkeypatch):
    """Every test gets its own conversation/usage DB: one test's history can never reach another
    test's prompt through the shared OPSCOPILOT_SESSION above."""
    monkeypatch.setenv("OPSCOPILOT_DB", str(tmp_path / "opscopilot.db"))


def pytest_configure(config):
    config.addinivalue_line("markers", "step(n): the workshop step this single test belongs to")


def pytest_collection_modifyitems(config, items):
    for item in items:
        mark = item.get_closest_marker("step")
        if mark and mark.args and int(mark.args[0]) > STEP:
            n = int(mark.args[0])
            item.add_marker(pytest.mark.skip(reason=f"należy do kroku {n:02d}"))
