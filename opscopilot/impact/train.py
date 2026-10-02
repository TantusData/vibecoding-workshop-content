"""opscopilot/impact/train.py — train the impact regressors from the incident history.

Purpose:      Fits one GradientBoostingRegressor per target (downtime_min, eur_impact) on
              data/incidents/history.csv and saves them with the feature contract to
              var/impact_model.joblib. The model is not shipped as a binary: it is trained here,
              in about a second, the first time anything needs it (see estimate.load_model).
              The corrupt variants (shuffled / leaked) are only ever cross-validated, for the
              data-quality lesson — never saved.
Entry points: MODEL_PATH, TARGETS, load_rows(variant), cross_val(rows, extra), train(rows, extra),
              train_and_save(path)
Depends on:   scikit-learn, joblib, numpy, opscopilot.impact.features, opscopilot.config (seed)
Used by:      opscopilot.impact.estimate (first use), scripts/train_impact.py
Invariants:   Deterministic (random_state = RANDOM_SEED): the same data gives the same model and
              the same numbers on every box. Only the clean variant is ever saved.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_score

from opscopilot.config import settings
from opscopilot.impact.features import FEATURE_NAMES, rows_to_xy

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "incidents"
MODEL_PATH = Path(os.environ.get("OPSCOPILOT_IMPACT_MODEL", ROOT / "var" / "impact_model.joblib"))
TARGETS = ["downtime_min", "eur_impact"]


def load_rows(variant: str) -> list[dict]:
    name = "history.csv" if variant == "clean" else f"history_{variant}.csv"
    with (DATA / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def xy(rows: list[dict], target: str, extra: list[str]) -> tuple[np.ndarray, np.ndarray]:
    x, y = rows_to_xy(rows, target)
    if extra:
        x = np.hstack([x, np.asarray([[float(r[c]) for c in extra] for r in rows])])
    return x, y


def make_model() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.9,
        random_state=settings.random_seed,
    )


def cross_val(rows: list[dict], extra: list[str]) -> dict[str, float]:
    cv = KFold(n_splits=5, shuffle=True, random_state=settings.random_seed)
    return {
        t: float(np.mean(cross_val_score(make_model(), *xy(rows, t, extra), cv=cv, scoring="r2")))
        for t in TARGETS
    }


def train(rows: list[dict], extra: list[str]) -> dict:
    names = FEATURE_NAMES + extra
    models = {}
    for t in TARGETS:
        x, y = xy(rows, t, extra)
        models[t] = make_model().fit(x, y)
    return {"models": models, "feature_names": names, "targets": TARGETS, "n_rows": len(rows)}


def train_and_save(path: Path = MODEL_PATH) -> Path:
    """Train on the clean history and save the bundle; returns the path written."""
    rows = load_rows("clean")
    bundle = train(rows, [])
    bundle["cv_r2"] = cross_val(rows, [])  # kept with the model: what "good" meant when trained
    bundle["trained_on"] = "data/incidents/history.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return path
