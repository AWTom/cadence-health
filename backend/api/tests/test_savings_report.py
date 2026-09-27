"""Deterministic savings math used by the report's calculate_savings tool."""
import pytest

from api.savings_report import calculate_savings

CFG = {
    "roi": {
        "cost_per_injurious_fall": 10000, "cost_per_non_injurious_fall": 1000,
        "annual_fall_prob_base": 0.1, "annual_fall_prob_per_point": 0.01, "annual_fall_prob_cap": 0.9,
        "injurious_fall_fraction": {"Low": 0.05, "Medium": 0.1, "High": 0.2},
    },
    "interventions": {"pt_exercise_fall_reduction": 0.25, "bed_alarm_fall_reduction": 0.2,
                      "hip_protector_injury_reduction": 0.5},
}
PATIENTS = [
    {"bed": "114", "name": "A", "care_level": 5, "fall_score": 80, "injury_level": "High"},
    {"bed": "105", "name": "B", "care_level": 1, "fall_score": 5, "injury_level": "Low"},
]


def test_single_intervention():
    r = calculate_savings(PATIENTS, CFG, ["114"], ["pt_exercise"])["residents"][0]
    # p=0.9 (capped), baseline cost 0.9*(0.2*10000+0.8*1000)=2520; after p=0.675 → 1890
    assert r["baseline_falls_per_year"] == 0.9
    assert r["falls_avoided_per_year"] == pytest.approx(0.225)
    assert r["savings_usd_per_year"] == 630


def test_interventions_combine_multiplicatively():
    out = calculate_savings(PATIENTS, CFG, ["114"], ["pt_exercise", "bed_alarm"], ["hip_protector"])
    assert out["fall_reduction_applied"] == 0.4          # 1 - 0.75*0.8
    assert out["injury_reduction_applied"] == 0.5


def test_totals_and_unknown_rooms():
    out = calculate_savings(PATIENTS, CFG, ["114", "105", "999"], ["pt_exercise"])
    assert [r["room"] for r in out["residents"]] == ["114", "105"]
    assert out["totals"]["savings_usd_per_year"] == sum(r["savings_usd_per_year"] for r in out["residents"])
