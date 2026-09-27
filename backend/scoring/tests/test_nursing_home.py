"""Tests for nursing home scoring (scoring mechanics v0.2, section 3)."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from scoring.models import ScoringConfig
from scoring.nursing_home import Med, ResidentState, score_unit

CONFIG_PATH = Path(__file__).parents[2] / "scoring_config.yaml"
NOW = datetime(2026, 9, 26, 14, 0, 0)


@pytest.fixture
def cfg() -> ScoringConfig:
    raw = yaml.safe_load(CONFIG_PATH.read_text())
    return ScoringConfig(version=raw["version"], raw=raw)


def mrs_a() -> ResidentState:
    """Section 5 worked example: 86F, BMI 20, walker, gets up alone, fell 3 weeks ago."""
    return ResidentState(
        patient_id="A", age=86, female=True, mds_assessed_at=NOW - timedelta(days=30),
        fall_dates=[NOW - timedelta(days=21)],
        fall_mobility="needs_help_gets_up_alone", walking="independent", transfers="independent",
        adl="independent", cognition="moderate", bladder="continent", bmi=20.0,
        meds=[
            Med("sertraline", {"ssri", "antidepressant"}),
            Med("lorazepam", {"benzodiazepine"}, started_at=NOW - timedelta(days=4)),
            Med("apixaban", {"anticoagulant"}),
        ],
    )


def mr_b() -> ResidentState:
    """Section 5 worked example: 78M, bedbound, total dependence, BMI 27, one antipsychotic."""
    return ResidentState(
        patient_id="B", age=78, female=False, mds_assessed_at=NOW - timedelta(days=30),
        fall_mobility="cannot_stand", walking="total", transfers="total", adl="total",
        bladder="total", bmi=27.0, meds=[Med("quetiapine", {"antipsychotic"})],
    )


def average(pid: str) -> ResidentState:
    return ResidentState(
        patient_id=pid, age=84, female=False, mds_assessed_at=NOW - timedelta(days=30),
        fall_mobility="aid_or_supervision", walking="limited", transfers="limited",
        adl="extensive_2", bladder="frequent", bmi=25.0,
    )


def by_id(results):
    return {r.patient_id: r for r in results}


class TestWorkedExample:
    def test_mrs_a(self, cfg):
        facility = [mrs_a(), mr_b()] + [average(f"X{i}") for i in range(8)]
        a = by_id(score_unit(facility, NOW, cfg))["A"]
        assert a.fall_score == 80 and a.fall_level == "High"
        assert a.bone_points == 60 and a.bone_level == "High"
        assert a.bleed_level == "High"          # apixaban + fall within 30 days
        assert a.injury_level == "High"
        assert a.care_level == 5

    def test_mr_b(self, cfg):
        facility = [mrs_a(), mr_b()] + [average(f"X{i}") for i in range(8)]
        b = by_id(score_unit(facility, NOW, cfg))["B"]
        assert b.fall_score == 5 and b.fall_level == "Low"
        assert b.bone_points == 3 and b.bone_level == "Low"
        assert b.bleed_level == "Low"
        assert b.care_level == 1

    def test_ehi_uses_bone_percentile(self, cfg):
        results = score_unit([mrs_a(), mr_b()], NOW, cfg)
        a = by_id(results)["A"]
        assert a.bone_percentile == 75.0   # mid-rank of 2
        assert a.ehi == 60.0               # 80 x 75 / 100


class TestFallScore:
    def test_cannot_stand_scores_zero_for_mobility(self, cfg):
        b = score_unit([mr_b()], NOW, cfg)[0]
        assert "mobility" not in [f.id for f in b.factors]

    def test_drug_classes_grouped(self, cfg):
        r = average("R")
        r.meds = [Med("lorazepam", {"benzodiazepine"}), Med("zolpidem", {"sleep"})]  # both "sedatives"
        f = next(f for f in score_unit([r], NOW, cfg)[0].factors if f.id == "fall_risk_meds")
        assert f.points == 5

    def test_three_plus_classes(self, cfg):
        r = average("R")
        r.meds = [Med(n, {c}) for n, c in [("a", "opioid"), ("b", "antipsychotic"), ("c", "diuretic"), ("d", "anticonvulsant")]]
        f = next(f for f in score_unit([r], NOW, cfg)[0].factors if f.id == "fall_risk_meds")
        assert f.points == 15

    def test_recent_change_capped(self, cfg):
        r = average("R")
        r.meds = [Med("oxycodone", {"opioid"}, started_at=NOW - timedelta(days=2))]
        r.acute_changes = [("UTI, started nitrofurantoin", NOW - timedelta(days=1)),
                           ("Hospital return", NOW - timedelta(days=3))]
        f = next(f for f in score_unit([r], NOW, cfg)[0].factors if f.id == "recent_change")
        assert f.points == 20

    def test_old_change_ignored(self, cfg):
        r = average("R")
        r.acute_changes = [("Fever", NOW - timedelta(days=10))]
        assert "recent_change" not in [f.id for f in score_unit([r], NOW, cfg)[0].factors]

    def test_fall_31_to_180_days(self, cfg):
        r = average("R")
        r.fall_dates = [NOW - timedelta(days=90)]
        f = next(f for f in score_unit([r], NOW, cfg)[0].factors if f.id == "recent_fall")
        assert f.points == 15

    def test_diuretic_given_today_triggers_bathroom(self, cfg):
        r = average("R")
        r.meds = [Med("furosemide", {"diuretic"}, last_given_at=NOW - timedelta(hours=2))]
        assert "bathroom_urgency" in [f.id for f in score_unit([r], NOW, cfg)[0].factors]

    def test_wandering_is_severe_cognition(self, cfg):
        r = average("R")
        r.wanders = True
        f = next(f for f in score_unit([r], NOW, cfg)[0].factors if f.id == "cognition")
        assert f.points == 15

    def test_overdue_mds_is_data_gap(self, cfg):
        r = average("R")
        r.mds_assessed_at = NOW - timedelta(days=120)
        res = score_unit([r], NOW, cfg)[0]
        assert "MDS assessment overdue" in res.data_gaps
        assert "data_gap" in [f.id for f in res.factors]

    def test_risk_rising(self, cfg):
        r = mrs_a()
        r.fall_score_7d_ago = 60
        assert score_unit([r], NOW, cfg)[0].risk_rising
        r.fall_score_7d_ago = 70
        assert not score_unit([r], NOW, cfg)[0].risk_rising


class TestInjury:
    def test_bone_injury_mode_excludes_fall_and_wandering(self, cfg):
        r = average("R")
        r.fall_dates, r.wanders = [NOW - timedelta(days=5)], True
        ids = [f.id for f in score_unit([r], NOW, cfg)[0].factors]
        assert "bone_previous_fall" not in ids and "bone_wandering" not in ids

    def test_bone_full_mode_includes_them(self, cfg):
        cfg.raw["nursing_home"]["bone"]["mode"] = "full"
        r = average("R")
        r.fall_dates, r.wanders = [NOW - timedelta(days=5)], True
        ids = [f.id for f in score_unit([r], NOW, cfg)[0].factors]
        assert "bone_previous_fall" in ids and "bone_wandering" in ids

    def test_percentile_bands(self, cfg):
        # 10 residents with distinct bone points: top 2 High, next 3 Medium, rest Low
        residents = []
        for i in range(10):
            r = mr_b()
            r.patient_id, r.bmi = f"R{i}", 30.0
            r.walking = ["total", "extensive", "limited", "independent"][min(i // 3, 3)]
            r.transfers = "independent" if i % 3 == 2 else "total"
            r.female = i >= 5
            residents.append(r)
        levels = sorted((res.bone_points, res.bone_level) for res in score_unit(residents, NOW, cfg))
        assert [lvl for _, lvl in levels].count("High") == 2
        assert levels[-1][1] == "High" and levels[0][1] == "Low"

    def test_anticoagulant_alone_is_medium_bleed(self, cfg):
        r = average("R")
        r.meds = [Med("warfarin", {"anticoagulant"})]
        assert score_unit([r], NOW, cfg)[0].bleed_level == "Medium"

    def test_dual_antiplatelet_is_high_bleed(self, cfg):
        r = average("R")
        r.meds = [Med("aspirin", {"antiplatelet"}), Med("clopidogrel", {"antiplatelet"})]
        assert score_unit([r], NOW, cfg)[0].bleed_level == "High"

    def test_missing_bmi_is_data_gap(self, cfg):
        r = average("R")
        r.bmi = None
        assert "BMI missing" in score_unit([r], NOW, cfg)[0].data_gaps
