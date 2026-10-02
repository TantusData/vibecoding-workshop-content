"""scripts/train_impact.py — cross-validate the impact regressor; save the clean one.

Purpose:      The command-line face of opscopilot.impact.train. With no flags it trains on the
              clean history, prints 5-fold R² and the top drivers, and saves
              var/impact_model.joblib. `--variant shuffled|leaked --eval` trains on the corrupt
              datasets and prints 5-fold R² so the corrupt-data lesson is a number, not a story:
              shuffled labels -> R² below zero; the leaked column -> R² near 1 with that column as
              the top driver, i.e. a model that would be useless the moment it is used before
              the fact.
Entry points: main()
Depends on:   opscopilot.impact.train
Used by:      whoever evaluates the model (`python scripts/train_impact.py --variant leaked --eval`)
Invariants:   Deterministic (random_state = RANDOM_SEED). Only the clean variant is ever saved.
"""

from __future__ import annotations

import sys
from pathlib import Path

# run as `python scripts/<name>.py` from the project folder, with nothing installed: make the
# project importable (under uv it already is; this line then changes nothing)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import sys

from opscopilot.impact.train import MODEL_PATH, TARGETS, cross_val, load_rows, train, train_and_save


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["clean", "shuffled", "leaked"], default="clean")
    ap.add_argument(
        "--eval", action="store_true", help="print 5-fold R² and top drivers, do not save"
    )
    args = ap.parse_args()
    rows = load_rows(args.variant)
    extra = ["logged_cost_estimate_eur"] if args.variant == "leaked" else []
    scores = cross_val(rows, extra)
    bundle = train(rows, extra)
    print(f"variant={args.variant} rows={len(rows)}")
    for t in TARGETS:
        imp = bundle["models"][t].feature_importances_
        top = sorted(zip(bundle["feature_names"], imp, strict=True), key=lambda p: -p[1])[:3]
        print(
            f"  {t:13s} R²(cv)={scores[t]:6.3f}  top drivers: "
            + ", ".join(f"{n}={v:.2f}" for n, v in top)
        )
    if args.eval or args.variant != "clean":
        return 0
    print(f"saved {train_and_save(MODEL_PATH)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
