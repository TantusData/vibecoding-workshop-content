"""scripts/make_incidents.py — generate the historical incident dataset and two corrupt variants.

Purpose:      Seeded (RANDOM_SEED) synthetic history for the impact model: `history.csv` (clean),
              `history_shuffled.csv` (targets shuffled across rows — the labels no longer belong to
              their features) and `history_leaked.csv` (adds `logged_cost_estimate_eur`, a post-hoc
              column that is only known *after* the incident and therefore must never be a
              feature). The 20 hand-checked rows in `_seed_rows.csv` are appended verbatim.
Entry points: main(), generate(n, rng) -> list[dict], FORMULA (documented below)
Depends on:   numpy, csv (stdlib), opscopilot.config (seed)
Used by:      Makefile `data-incidents`; committed output in data/incidents/
Invariants:   Deterministic for a given seed. eur_impact = downtime_min * line rate + part cost.
              orders_at_risk = ceil(downtime_min / 45). The seed rows are never regenerated.
"""

from __future__ import annotations

import sys
from pathlib import Path

# run as `python scripts/<name>.py` from the project folder, with nothing installed: make the
# project importable (under uv it already is; this line then changes nothing)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import csv
import math
import sys
from pathlib import Path

import numpy as np

from opscopilot.config import settings

OUT = Path(__file__).resolve().parent.parent / "data" / "incidents"
SEED_ROWS = OUT / "_seed_rows.csv"
FIELDS = [
    "incident_id",
    "date",
    "line",
    "shift",
    "category",
    "machine_age_years",
    "part_cost_eur",
    "crew_size",
    "time_of_day_hours",
    "historical_mtbf_days",
    "downtime_min",
    "eur_impact",
    "orders_at_risk",
]

# FORMULA — downtime_min = base(category) + line effect + 6*age - 18*(crew-1) + night + noise
BASE = {"mechanical": 70.0, "electrical": 60.0, "software": 35.0, "material": 20.0, "other": 25.0}
LINE_EFFECT = {"L1": 0.0, "L2": -8.0, "L3": 25.0}  # the palletiser line is the slow one to recover
EUR_PER_MIN = {"L1": 60.0, "L2": 50.0, "L3": 70.0}
MTBF = {"L1": 45.0, "L2": 60.0, "L3": 21.0}
AGE = {"L1": 4.5, "L2": 2.4, "L3": 8.2}
CATEGORY_P = [0.38, 0.22, 0.18, 0.12, 0.10]
CATEGORIES = list(BASE)


def generate(n: int, rng: np.random.Generator) -> list[dict]:
    rows = []
    start = np.datetime64("2023-01-09")
    for i in range(n):
        line = rng.choice(["L1", "L2", "L3"], p=[0.35, 0.35, 0.30])
        cat = rng.choice(CATEGORIES, p=CATEGORY_P)
        shift = rng.choice(["day", "night"], p=[0.6, 0.4])
        age = round(float(AGE[line] + rng.normal(0, 0.6)), 1)
        crew = int(rng.choice([1, 2, 3], p=[0.35, 0.5, 0.15]))
        hour = int(rng.integers(6, 22)) if shift == "day" else int(rng.integers(0, 6))
        part = 0.0 if cat in ("software", "material") else round(float(rng.gamma(2.0, 250.0)), 0)
        mtbf = round(float(MTBF[line] + rng.normal(0, 4)), 0)
        downtime = (
            BASE[cat]
            + LINE_EFFECT[line]
            + 6.0 * age
            - 18.0 * (crew - 1)
            + (15.0 if shift == "night" else 0.0)
            + rng.normal(0, 12)
        )
        downtime = round(max(10.0, downtime), 0)
        eur = round(downtime * EUR_PER_MIN[line] + part, 0)
        rows.append(
            {
                "incident_id": f"H-{1000 + i}",
                "date": str(start + np.timedelta64(int(rng.integers(0, 900)), "D")),
                "line": line,
                "shift": shift,
                "category": cat,
                "machine_age_years": age,
                "part_cost_eur": part,
                "crew_size": crew,
                "time_of_day_hours": hour,
                "historical_mtbf_days": mtbf,
                "downtime_min": downtime,
                "eur_impact": eur,
                "orders_at_risk": math.ceil(downtime / 45),
            }
        )
    rows.sort(key=lambda r: r["date"])
    return rows


def write(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main(n: int = 300) -> int:
    rng = np.random.default_rng(settings.random_seed)
    rows = generate(n, rng)
    with SEED_ROWS.open(encoding="utf-8") as fh:
        rows += list(csv.DictReader(fh))
    write(OUT / "history.csv", rows, FIELDS)

    # variant 1: shuffled labels — every target column permuted independently of the features
    perm = rng.permutation(len(rows))
    shuffled = [dict(r) for r in rows]
    for col in ("downtime_min", "eur_impact", "orders_at_risk"):
        vals = [rows[j][col] for j in perm]
        for r, v in zip(shuffled, vals, strict=True):
            r[col] = v
    write(OUT / "history_shuffled.csv", shuffled, FIELDS)

    # variant 2: leaked feature — a post-hoc cost log that is ~the label with 3% noise
    leaked = []
    for r in rows:
        r2 = dict(r)
        r2["logged_cost_estimate_eur"] = round(
            float(r["eur_impact"]) * float(rng.normal(1.0, 0.03)), 0
        )
        leaked.append(r2)
    write(OUT / "history_leaked.csv", leaked, FIELDS + ["logged_cost_estimate_eur"])
    print(f"wrote {len(rows)} rows x 3 variants to {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
