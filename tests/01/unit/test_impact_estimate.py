"""Fixed-input tests for opscopilot.impact — the model is loaded, never trained; no MCP, no LLM."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from norddesk_mcp import store
from opscopilot.impact import estimate as impact
from opscopilot.impact.features import FEATURE_NAMES, featurize, incident_from_ticket
from opscopilot.schema import Incident

L3_MECH_NIGHT = Incident(
    line="L3",
    shift="night",
    category="mechanical",
    machine_age_years=8.5,
    part_cost_eur=420.0,
    crew_size=2,
    time_of_day_hours=3,
    historical_mtbf_days=21.0,
)
L2_SOFT_DAY = Incident(
    line="L2",
    shift="day",
    category="software",
    machine_age_years=2.1,
    part_cost_eur=0.0,
    crew_size=1,
    time_of_day_hours=11,
    historical_mtbf_days=60.0,
)


def test_featurize_is_the_frozen_contract():
    vec = featurize(L3_MECH_NIGHT)
    assert len(vec) == len(FEATURE_NAMES) == 15
    assert dict(zip(FEATURE_NAMES, vec, strict=True)) == {
        "machine_age_years": 8.5,
        "part_cost_eur": 420.0,
        "crew_size": 2.0,
        "time_of_day_hours": 3.0,
        "historical_mtbf_days": 21.0,
        "line=L1": 0.0,
        "line=L2": 0.0,
        "line=L3": 1.0,
        "shift=day": 0.0,
        "shift=night": 1.0,
        "category=mechanical": 1.0,
        "category=electrical": 0.0,
        "category=software": 0.0,
        "category=material": 0.0,
        "category=other": 0.0,
    }


def test_model_loads_with_the_matching_feature_contract():
    bundle = impact.load_model()
    assert list(bundle["feature_names"]) == FEATURE_NAMES
    assert set(bundle["models"]) == {"downtime_min", "eur_impact"}
    assert bundle["cv_r2"]["downtime_min"] > 0.7 and bundle["cv_r2"]["eur_impact"] > 0.8


def test_estimate_is_deterministic_and_plausible():
    a = impact.estimate(L3_MECH_NIGHT)
    b = impact.estimate(L3_MECH_NIGHT)
    assert a == b
    assert 120 <= a.downtime_min <= 260  # the generator's L3 mechanical night band
    assert a.eur_impact > a.downtime_min * 60  # L3 rate is 70 EUR/min + part cost
    assert a.orders_at_risk == -(-a.downtime_min // 45)
    assert len(a.drivers) == 4


def test_a_quick_software_fix_on_l2_costs_far_less_than_a_palletiser_breakdown():
    big = impact.estimate(L3_MECH_NIGHT)
    small = impact.estimate(L2_SOFT_DAY)
    assert small.downtime_min < big.downtime_min / 2
    assert small.eur_impact < big.eur_impact / 3


def test_drivers_point_at_the_line_and_the_old_machine_for_inc_1042_like_incidents():
    names = dict(impact.drivers(L3_MECH_NIGHT, k=8))
    assert names["line=L3"] > 0  # L3 is slower to recover than L1/L2
    assert names["machine_age_years"] > 0  # an old machine adds minutes vs the median
    assert names["crew_size"] == pytest.approx(0.0, abs=5)  # crew of 2 is the baseline


def test_incident_from_ticket_maps_inc_1042(tmp_path, monkeypatch):
    monkeypatch.setenv("NORDDESK_STORE", str(tmp_path / "s.json"))
    store.init_store(force=True)
    ticket = store.get_ticket("INC-1042")
    inc = incident_from_ticket(ticket, assets=store.load()["assets"])
    assert inc == Incident(
        line="L3",
        shift="day",
        category="mechanical",
        machine_age_years=9.5,
        part_cost_eur=250.0,
        crew_size=2,
        time_of_day_hours=6,
        historical_mtbf_days=21.0,
    )
    mes = incident_from_ticket(store.get_ticket("INC-1039"), assets=store.load()["assets"])
    assert (mes.line, mes.category, mes.shift) == ("L2", "software", "night")


def test_explain_reads_like_a_sentence():
    text = impact.explain(L3_MECH_NIGHT)
    assert text.startswith("Estimated downtime ") and "EUR" in text and "Drivers" in text


def test_shuffled_and_leaked_variants_exist_and_are_what_they_claim(tmp_path):
    root = Path("data/incidents")
    clean = list(csv.DictReader((root / "history.csv").open()))
    shuffled = list(csv.DictReader((root / "history_shuffled.csv").open()))
    leaked = list(csv.DictReader((root / "history_leaked.csv").open()))
    assert len(clean) == len(shuffled) == len(leaked) == 320
    # same label multiset, different assignment
    assert sorted(r["downtime_min"] for r in clean) == sorted(r["downtime_min"] for r in shuffled)
    assert (
        sum(a["downtime_min"] != b["downtime_min"] for a, b in zip(clean, shuffled, strict=True))
        > 250
    )
    # the leaked column is ~the label
    y = np.array([float(r["eur_impact"]) for r in leaked])
    leak = np.array([float(r["logged_cost_estimate_eur"]) for r in leaked])
    assert np.corrcoef(y, leak)[0, 1] > 0.99
