"""opscopilot/impact/estimate.py — downtime / € estimate for an incident from the pre-trained model.

Purpose:      Loads var/impact_model.joblib once (two GradientBoostingRegressors: downtime_min
              and eur_impact, plus the feature contract), predicts for one `Incident`, and
              explains the number with drivers: for each feature, how much the prediction moves
              when that feature is set to the training median — a local, model-agnostic
              attribution that a shift lead can read ("older machine: +14 min").
Entry points: estimate(incident) -> ImpactEstimate, load_model() -> dict, explain(incident),
              MODEL_PATH, drivers(incident, k)
Depends on:   joblib, numpy, scikit-learn (via the pickled model), opscopilot.impact.features,
              opscopilot.schema.{Incident, ImpactEstimate}
Used by:      opscopilot.cli (the `impact_estimate` step of ask, `opscopilot impact`)
Invariants:   Deterministic: same Incident -> same numbers. The joblib's feature_names must equal
              FEATURE_NAMES or load_model() raises (train/serve contract). If the file is absent
              it is trained once (about a second, opscopilot.impact.train) — no binary is shipped.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import joblib
import numpy as np

from opscopilot.impact.features import FEATURE_NAMES, NUMERIC, featurize
from opscopilot.impact.train import MODEL_PATH, train_and_save
from opscopilot.schema import ImpactEstimate, Incident

# training-set medians used as the "typical incident" baseline for driver attribution
BASELINE = {
    "machine_age_years": 4.6,
    "part_cost_eur": 250.0,
    "crew_size": 2.0,
    "time_of_day_hours": 11.0,
    "historical_mtbf_days": 45.0,
}


@lru_cache(maxsize=1)
def load_model() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        train_and_save(MODEL_PATH)
    bundle = joblib.load(MODEL_PATH)
    if list(bundle["feature_names"]) != FEATURE_NAMES:
        raise ValueError(
            "impact model feature contract does not match impact.features.FEATURE_NAMES"
        )
    return bundle


def _predict(vec: np.ndarray) -> tuple[float, float]:
    models = load_model()["models"]
    x = vec.reshape(1, -1)
    return float(models["downtime_min"].predict(x)[0]), float(models["eur_impact"].predict(x)[0])


def drivers(inc: Incident, k: int = 4) -> list[tuple[str, float]]:
    """Top-k features by |effect|: minutes gained/lost vs. setting that feature to its baseline."""
    base_vec = featurize(inc)
    base_pred, _ = _predict(base_vec)
    effects: list[tuple[str, float]] = []
    for name in NUMERIC:
        alt = base_vec.copy()
        alt[FEATURE_NAMES.index(name)] = BASELINE[name]
        effects.append((name, round(base_pred - _predict(alt)[0], 1)))
    for group, current in (("line", inc.line), ("category", inc.category), ("shift", inc.shift)):
        # vs. the average over the other values of the same categorical
        others = [
            n for n in FEATURE_NAMES if n.startswith(f"{group}=") and n != f"{group}={current}"
        ]
        alts = []
        for other in others:
            alt = base_vec.copy()
            alt[FEATURE_NAMES.index(f"{group}={current}")] = 0.0
            alt[FEATURE_NAMES.index(other)] = 1.0
            alts.append(_predict(alt)[0])
        effects.append((f"{group}={current}", round(base_pred - float(np.mean(alts)), 1)))
    effects.sort(key=lambda e: -abs(e[1]))
    return effects[:k]


def estimate(inc: Incident) -> ImpactEstimate:
    downtime, eur = _predict(featurize(inc))
    downtime = max(10.0, round(downtime, 0))
    return ImpactEstimate(
        downtime_min=downtime,
        eur_impact=max(0.0, round(eur, 0)),
        orders_at_risk=math.ceil(downtime / 45),
        drivers=drivers(inc),
    )


def explain(inc: Incident) -> str:
    """One paragraph a human can read: the numbers, then the drivers in minutes."""
    est = estimate(inc)
    parts = [f"{name}: {'+' if v >= 0 else ''}{v:.0f} min" for name, v in est.drivers]
    return (
        f"Estimated downtime {est.downtime_min:.0f} min, about EUR {est.eur_impact:,.0f}, "
        f"{est.orders_at_risk} order(s) at risk. Drivers vs. a typical incident — "
        + "; ".join(parts)
        + "."
    )
