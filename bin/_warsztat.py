"""Shared code for the workshop's commands: krok, sprawdz, zakoncz, checkpoint, undo.

ENGLISH TESTER BRANCH (tester-en): a translation of the Polish course's bin/_warsztat.py, built by
scripts/build_tester_en.py. Same logic; differences: everything printed is English, the step
texts shown in the terminal (where you are, first action, manual checks) come from GUIDE_EN.md
(the English guide, one block per unit) instead of the Polish page, the agent's current-stage
file is English, and the Polish step page stays on disk as the original.

Paths: the material is this repository (~/workshop, refreshed on every boot and never edited by
participants); the participant's project is ~/work/project (OPSCOPILOT_PROJECT overrides it, for
tests of these scripts). Standard library only: these run before anything else is known to work.

Step materials (steps/NN, specs/NN, tests/NN) are NOT in the clone: each lives under a ref
refs/steps/NN that no clone or default fetch downloads, and `krok` fetches it on demand — an agent
cannot read ahead into a later step's page, contract or tests. Steps 03 and 07 have a part B
(03b, 07b) that is unlocked only after the part-A discovery. Once fetched, the files sit in
git-ignored folders; `materialy.sha256` (committed) pins their content, so an edited test is
detected without the manifest revealing anything. The agent is pointed (aktualny-etap.md) at
specs/ and tests/ only — steps/ is the participant's page — and knows the units as stages of
Tomasz's plan (STAGES), never as course steps (TITLES).
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from fnmatch import fnmatch
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
PROJECT = Path(os.environ.get("OPSCOPILOT_PROJECT", Path.home() / "work" / "project"))
SEED = WS / "seed"
STEPS = 8
UNDO_FILE = "workshop-undo"  # inside the project's .git: never part of the tree, never committed
DONE_FILE = "workshop-done"
IDENTITY = ("Workshop", "coder@workshop.local")  # invented, local only — never pushed anywhere
MANIFEST = WS / "materialy.sha256"
CURRENT = Path(".clinerules") / "aktualny-etap.md"
GUIDE = WS / "GUIDE_EN.md"
SWAP = WS / "english" / "swap.txt"

# every unit of material, in the order of the day (a unit = one hidden ref)
UNITS = ["01", "02", "03", "03b", "04", "05", "06", "07", "07b", "08"]
SPLIT = {"03", "07"}  # steps with a part B
TITLES = {
    "01": "Read the note, not the whole repository — and make the project look like yours",
    "02": "Give the assistant the ticket system",
    "03": "Let it remember the conversation",
    "03b": "Memory that lies — and how to fix it",
    "04": "A tool loop with a limit",
    "05": "Decide what it must refuse",
    "06": "Guardrails and audit",
    "07": "Give it the wiki: searching the documentation",
    "07b": "Why didn't it find it? Retrieval quality",
    "08": "We finished Tomasz's project",
}
# the same units as the agent sees them: stages of Tomasz's plan (HANDOVER_NOTE.md), in the
# project's own words — no course vocabulary reaches the agent
STAGES = {
    "01": "Taking over the project: Tomasz's note versus the code",
    "02": "NordDesk client (the ticket system)",
    "03": "Conversation memory",
    "03b": "Conversation memory — fresh data instead of memory",
    "04": "A tool loop with a limit",
    "05": "What the assistant must refuse — the decision set",
    "06": "Guardrails and audit",
    "07": "Wiki search (RAG)",
    "07b": "Wiki search — chunk quality",
    "08": "Polish: trace, costs, impact model, shift report",
}


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    sys.exit(code)


def label(unit: str) -> str:
    """'03' -> '03' (or '03, part A' for a split step), '03b' -> '03, part B'."""
    if unit.endswith("b"):
        return f"{unit[:2]}, part B"
    return f"{unit}, part A" if unit in SPLIT else unit


def parse(argv: list[str], usage: str, *, part_a_of_split: bool) -> str:
    """The unit an argument names. '3a' -> '03'; '3b' -> '03b'; '4' -> '04'.

    A bare number of a split step means part A for `krok`/`zakoncz` (you start and finish part A
    first) and the whole step for `sprawdz`/`checkpoint` (part_a_of_split=False)."""
    args = [a for a in argv if not a.startswith("-")]
    m = re.fullmatch(r"0?([1-8])([abAB]?)", args[0]) if len(args) == 1 else None
    if not m:
        fail(usage, 2)
    n, part = f"{int(m.group(1)):02d}", m.group(2).lower()
    if part and n not in SPLIT:
        fail(f"Step {n} has no parts A/B.\n\n{usage}", 2)
    if part == "b" or (not part and n in SPLIT and not part_a_of_split):
        return n + "b"
    return n


def units_upto(unit: str) -> list[str]:
    return UNITS[: UNITS.index(unit) + 1]


def unlocked(unit: str) -> bool:
    return (WS / "steps" / unit / "README.md").is_file()


def git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run git; commits get the local workshop identity if the machine has none configured."""
    ident: list[str] = []
    if args and args[0] == "commit":
        probe = subprocess.run(
            ["git", "config", "user.email"], cwd=cwd, capture_output=True, text=True
        )
        if not probe.stdout.strip():
            ident = ["-c", f"user.name={IDENTITY[0]}", "-c", f"user.email={IDENTITY[1]}"]
    return subprocess.run(
        ["git", *ident, *args], cwd=cwd, capture_output=True, text=True, check=check
    )


def remote() -> str:
    url = os.environ.get("WORKSHOP_REMOTE")
    if not url:
        url = git("remote", "get-url", "origin", cwd=WS).stdout.strip()
    if url and Path(url).is_dir():  # a local path (the build's own validation)
        url = Path(url).resolve().as_uri()
    return url


def fetch_refs(refs: list[str]) -> dict[str, dict[str, bytes]]:
    """{ref: {path: content}} for hidden refs, via a throw-away bare repo (nothing stays behind).
    An executable file is marked by an extra key `path + "\\0x"`."""
    out: dict[str, dict[str, bytes]] = {}
    with tempfile.TemporaryDirectory(prefix="warsztat-") as tmp:
        bare = Path(tmp) / "r.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        specs = [f"{ref}:refs/pobrane/{i}" for i, ref in enumerate(refs)]
        r = subprocess.run(
            ["git", "-C", str(bare), "fetch", "-q", "--depth", "1", "--no-tags", remote(), *specs],
            capture_output=True,
            text=True,
        )
        if r.returncode:
            fail(
                "Could not fetch the materials from the course repository.\n"
                "Check the connection and try again; if that does not help, call the trainer.\n"
                f"(git: {r.stderr.strip()[:300]})"
            )
        for i, ref in enumerate(refs):
            tar = subprocess.run(
                ["git", "-C", str(bare), "archive", f"refs/pobrane/{i}"],
                capture_output=True,
                check=True,
            ).stdout
            files: dict[str, bytes] = {}
            with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
                for m in tf.getmembers():
                    if m.isfile():
                        files[m.name] = tf.extractfile(m).read()  # type: ignore[union-attr]
                        if m.mode & 0o111:
                            files[m.name + "\0x"] = b""
            out[ref] = files
    return out


def unit_dirs(unit: str) -> list[Path]:
    return [WS / "steps" / unit, WS / "specs" / unit, WS / "tests" / unit]


def unlock(units: list[str], *, force: bool = False) -> list[str]:
    """Fetch and write the materials of `units` (skipping ones already present unless force).
    Returns the units written."""
    todo = [u for u in units if force or not unlocked(u)]
    if not todo:
        return []
    fetched = fetch_refs([f"refs/steps/{u}" for u in todo])
    for u in todo:
        for d in unit_dirs(u):  # a clean copy: nothing stale or planted survives
            if d.exists():
                for p in sorted(d.rglob("*"), reverse=True):
                    p.unlink() if p.is_file() or p.is_symlink() else p.rmdir()
        for path, data in fetched[f"refs/steps/{u}"].items():
            if path.endswith("\0x"):
                continue
            dst = WS / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
    return todo


def manifest() -> dict[str, str]:
    if not MANIFEST.exists():
        return {}
    out = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line.strip():
            sha, path = line.split(maxsplit=1)
            out[path] = sha
    return out


def tampered_materials() -> list[str]:
    """Unlocked step files that differ from the course's version, are missing, or were added."""
    pinned = manifest()
    problems = []
    for u in UNITS:
        if not unlocked(u):
            continue
        expected = {p for p in pinned if p.split("/")[1:2] == [u]}
        present = set()
        for d in unit_dirs(u):
            for p in d.rglob("*"):
                if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts:
                    rel = p.relative_to(WS).as_posix()
                    present.add(rel)
                    sha = hashlib.sha256(p.read_bytes()).hexdigest()
                    if rel not in pinned:
                        problems.append(f"?? {rel} (added)")
                    elif pinned[rel] != sha:
                        problems.append(f" M {rel} (changed)")
        problems += [f" D {rel} (deleted)" for rel in sorted(expected - present)]
    return problems


def section(unit: str, title: str) -> str:
    """The text of one `### title` subsection of the unit's block in GUIDE_EN.md (empty if
    absent). A block starts at the line `<!-- unit NN -->` and runs to the next one."""
    if not GUIDE.exists():
        return ""
    text = GUIDE.read_text(encoding="utf-8")
    block = re.search(
        rf"^<!-- unit {re.escape(unit)} -->\s*$(.*?)(?=^<!-- unit |\Z)", text, flags=re.M | re.S
    )
    if not block:
        return ""
    m = re.search(
        rf"^### {re.escape(title)}\s*$(.*?)(?=^##+ |\Z)", block.group(1), flags=re.M | re.S
    )
    return m.group(1).strip() if m else ""


def plain(text: str) -> str:
    """Markdown from a step page, readable in a terminal: no code fences, no bold markers."""
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
    return re.sub(r"\*\*(.+?)\*\*", r"\1", "\n".join(lines))


def check_arg(unit: str) -> str:
    """The `sprawdz`/`zakoncz` argument of a unit: '03' -> '3a', '03b' -> '3b', '04' -> '4'."""
    n = int(unit[:2])
    return f"{n}a" if unit in SPLIT else (f"{n}b" if unit.endswith("b") else str(n))


def write_current(project: Path, unit: str) -> None:
    """.clinerules/aktualny-etap.md — Cline reads .clinerules at every task, so it always knows
    which stage of Tomasz's plan is in progress, where its requirements and acceptance tests are,
    and what it must not do. Points at the agent's file (specs/), never at the person's page
    (steps/): the page holds discoveries and manual checks the agent must not do for them."""
    if not project.is_dir():
        return
    n = unit[:2]
    check = check_arg(unit)
    part = ", second part" if unit.endswith("b") else ""
    lines = [
        f"# Stage in progress: {int(n)}{part} of Tomasz's plan — {STAGES[unit]}",
        "",
        "This file is set by `~/workshop/bin/krok`; do not edit it.",
        "",
    ]
    for u in [n, unit] if unit.endswith("b") else [unit]:
        lines += [
            f"- Requirements, decisions and contract (in Polish): `~/workshop/specs/{u}/spec.md`",
            f"- Acceptance tests: `~/workshop/tests/{u}/` (read-only)",
        ]
    lines += [
        f"- Check after every change: `~/workshop/bin/sprawdz {check}`",
        "",
        "- Work on this stage only: earlier ones are finished, do not start later ones.",
        "- After a PASSED result, say briefly that the acceptance tests pass and that the person",
        "  you work with now does their own manual checks and closes the stage themselves with",
        f"  `~/workshop/bin/zakoncz {check}`. Do not list the manual checks, do not perform them",
        "  and do not judge their result.",
        "",
    ]
    path = project / CURRENT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def manual_checks(unit: str) -> list[str]:
    """The numbered items of the unit's "### Manual checks" subsection in GUIDE_EN.md."""
    checks = section(unit, "Manual checks")
    if not checks:
        return []
    items: list[str] = []
    for line in checks.splitlines():
        if re.match(r"^\d+\.\s", line):
            items.append(line)
        elif items:
            items[-1] += "\n" + line
    return [i.rstrip() for i in items]


def ensure_project_repo(project: Path) -> None:
    if not project.is_dir():
        fail(
            f"There is no project folder {project}.\n"
            "It should be created when the machine starts (a copy of ~/workshop/seed). "
            "Ask the trainer for help."
        )
    if not (project / ".git").exists():
        git("init", "-q", cwd=project)
        git("add", "-A", cwd=project)
        git("commit", "-q", "--allow-empty", "-m", "Project start", cwd=project)


def commit_all(project: Path, message: str) -> str:
    git("add", "-A", cwd=project)
    git("commit", "-q", "--allow-empty", "-m", message, cwd=project)
    return git("rev-parse", "HEAD", cwd=project).stdout.strip()


def keep_patterns() -> list[str]:
    lines = (WS / "keep.txt").read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def is_kept(rel: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat.endswith("/") and (rel + "/").startswith(pat):
            return True
        if fnmatch(rel, pat):
            return True
    return False


def is_participants(rel: str, project: Path, patterns: list[str]) -> bool:
    """A keep.txt path the participant actually made their own: present and not the seed copy.
    An untouched seed file is not protected, so a catch-up can still fill it in."""
    if not is_kept(rel, patterns):
        return False
    mine = project / rel
    if not mine.is_file():
        return False
    seed = SEED / rel
    return not seed.is_file() or seed.read_bytes() != mine.read_bytes()


def confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        fail("This command asks for confirmation — run it yourself in a terminal.", 2)
    try:
        answer = input(prompt)
    except EOFError:
        return False
    return answer.strip().lower() in ("yes", "y", "tak", "t")


def english_snapshot(snap: dict[str, bytes]) -> dict[str, bytes]:
    """A checkpoint snapshot with its Polish project files (the note, README, agent context,
    chat page, example rules and look) replaced by their English versions. english/swap.txt maps
    the sha256 of each known Polish file to the English file in ~/workshop; any other file —
    code, data, a Polish file this branch does not know — passes through unchanged."""
    if not SWAP.exists():
        return snap
    table = {}
    for line in SWAP.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            sha, rel = line.split(maxsplit=1)
            table[sha] = WS / rel
    out = dict(snap)
    for path, data in snap.items():
        english = table.get(hashlib.sha256(data).hexdigest())
        if english is not None and english.is_file():
            out[path] = english.read_bytes()
    return out
