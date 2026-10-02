"""opscopilot/impact/features.py — one deterministic feature vector per incident (shared by
training and inference).

Purpose:      Turns an `Incident` (the pydantic contract) into a fixed-order numeric vector:
              numeric columns as-is, categorical ones one-hot with a frozen vocabulary. Also maps
              a NordDesk ticket to an `Incident`, using the system/asset seed knowledge (line,
              machine age, MTBF) and a keyword rule for the category. Same code path for
              `train_impact.py` and `estimate()`, so train/serve skew is impossible by construction.
Entry points: FEATURE_NAMES, featurize(incident) -> np.ndarray, rows_to_xy(rows, target),
              incident_from_ticket(ticket, systems, assets) -> Incident, CATEGORY_KEYWORDS
Depends on:   numpy, opscopilot.schema.Incident
Used by:      opscopilot.impact.estimate, scripts/train_impact.py
Invariants:   FEATURE_NAMES order is part of the saved model's contract (`feature_names` in the
              joblib) and is asserted at load. Unknown category values raise, never silently zero.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import numpy as np

from opscopilot.schema import Incident

LINES = ["L1", "L2", "L3"]
SHIFTS = ["day", "night"]
CATEGORIES = ["mechanical", "electrical", "software", "material", "other"]
NUMERIC = [
    "machine_age_years",
    "part_cost_eur",
    "crew_size",
    "time_of_day_hours",
    "historical_mtbf_days",
]
FEATURE_NAMES: list[str] = (
    NUMERIC
    + [f"line={v}" for v in LINES]
    + [f"shift={v}" for v in SHIFTS]
    + [f"category={v}" for v in CATEGORIES]
)

# ticket -> category, first match wins (order matters: "software" before "mechanical" words)
CATEGORY_KEYWORDS: list[tuple[str, re.Pattern[str]]] = [
    (
        "software",
        re.compile(r"(?i)\b(mes|scada|erp|software|service|patch|hotfix|reboot|login|app)\b"),
    ),
    (
        "electrical",
        re.compile(
            r"(?i)\b(electrical|power|sensor|relay|circuit|drive|motor|fuse|light curtain)\b"
        ),
    ),
    (
        "material",
        re.compile(r"(?i)\b(film|ribbon|label stock|labels?|pallets? empty|material|packaging)\b"),
    ),
    (
        "mechanical",
        re.compile(
            r"(?i)\b(gripper|belt|jam|mechanical|bearing|conveyor|palletis[eo]r|stopped|"
            r"fault f\d+)\b"
        ),
    ),
]

# what the NordDesk seed knows about each system; anything else falls back to L1 defaults
SYSTEM_LINE = {
    "palletiser-l3": "L3",
    "label-printer-l2": "L2",
    "scada-l1": "L1",
    "mes-packing": "L2",
}
DEFAULT_MTBF = {"L1": 45.0, "L2": 60.0, "L3": 21.0}
DEFAULT_AGE = {"L1": 4.5, "L2": 2.4, "L3": 8.2}
MEDIAN_PART_COST = 250.0


def featurize(inc: Incident) -> np.ndarray:
    vec = [float(getattr(inc, n)) for n in NUMERIC]
    vec += [1.0 if inc.line == v else 0.0 for v in LINES]
    vec += [1.0 if inc.shift == v else 0.0 for v in SHIFTS]
    vec += [1.0 if inc.category == v else 0.0 for v in CATEGORIES]
    return np.asarray(vec, dtype=np.float64)


def rows_to_xy(rows: list[dict[str, Any]], target: str) -> tuple[np.ndarray, np.ndarray]:
    """CSV rows (strings) -> (X, y) using the very same featurize()."""
    x = np.vstack(
        [featurize(Incident(**{k: rows_i[k] for k in Incident.model_fields})) for rows_i in rows]
    )
    y = np.asarray([float(r[target]) for r in rows])
    return x, y


def category_from_text(text: str) -> str:
    for name, pattern in CATEGORY_KEYWORDS:
        if pattern.search(text):
            return name
    return "other"


def incident_from_ticket(
    ticket: dict[str, Any], assets: list[dict[str, Any]] | None = None
) -> Incident:
    """Map a NordDesk ticket to the model's contract. Unknowns get documented defaults."""
    line = SYSTEM_LINE.get(ticket.get("system") or "", "L1")
    created = ticket.get("created_at")
    hour = datetime.fromisoformat(created).hour if created else 12
    age = DEFAULT_AGE[line]
    for a in assets or []:
        if a.get("system") == ticket.get("system") and a.get("installed"):
            year, month = (int(p) for p in a["installed"].split("-")[:2])
            ref = datetime.fromisoformat(created) if created else datetime(2026, 1, 1)
            age = round((ref.year - year) + (ref.month - month) / 12, 1)
    return Incident(
        line=line,
        shift="day" if 6 <= hour < 22 else "night",
        category=category_from_text(f"{ticket.get('summary', '')} {ticket.get('description', '')}"),
        machine_age_years=age,
        part_cost_eur=MEDIAN_PART_COST,
        crew_size=2,
        time_of_day_hours=hour,
        historical_mtbf_days=DEFAULT_MTBF[line],
    )
