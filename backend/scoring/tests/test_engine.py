"""Unit tests for the FallGuard scoring engine."""
import pytest
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from scoring.models import (
    PatientState, ScoringConfig, Sex, ClinicalEvent, MedOrder, MedAdmin, Observation, Tier
)
from scoring.engine import score_patient

CONFIG_PATH = Path(__file__).parents[2] / "scoring_config.yaml"


@pytest.fixture
def cfg() -> ScoringConfig:
    raw = yaml.safe_load(CONFIG_PATH.read_text())
    return ScoringConfig(version=raw["version"], raw=raw)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 26, 14, 0, 0)


def _empty_patient(pid: str = "P_TEST", age: int = 40, sex: Sex = Sex.MALE) -> PatientState:
    return PatientState(patient_id=pid, encounter_id=f"E_{pid}", age=age, sex=sex)


class TestFLSFactors:
    def test_fall_this_admission(self, cfg, now):
        p = _empty_patient()
        p.events = [ClinicalEvent("fall_this_admission", "", "", "", now - timedelta(hours=2), "FallEvent")]
        result = score_patient(p, now, cfg)
        ids = [f.id for f in result.factors]
        assert "fall_this_admission" in ids

    def test_age_bands(self, cfg, now):
        for age, expected_id in [(64, None), (65, "age"), (75, "age"), (85, "age")]:
            p = _empty_patient(age=age)
            result = score_patient(p, now, cfg)
            ids = [f.id for f in result.factors]
            if expected_id:
                assert "age" in ids, f"Expected age factor for age {age}"
            else:
                assert "age" not in ids, f"Expected no age factor for age {age}"

    def test_cam_positive(self, cfg, now):
        p = _empty_patient()
        p.assessments = [Observation("55752-0", "positive", "", now - timedelta(hours=2), "survey")]
        result = score_patient(p, now, cfg)
        assert "cam_positive" in [f.id for f in result.factors]

    def test_cam_outside_window_ignored(self, cfg, now):
        p = _empty_patient()
        p.assessments = [Observation("55752-0", "positive", "", now - timedelta(hours=30), "survey")]
        result = score_patient(p, now, cfg)
        assert "cam_positive" not in [f.id for f in result.factors]

    def test_frid_cap(self, cfg, now):
        p = _empty_patient()
        p.active_medications = [
            MedOrder(f"drug_{i}", str(i), frid_classes=[f"class_{i}"])
            for i in range(10)
        ]
        result = score_patient(p, now, cfg)
        frid_factor = next((f for f in result.factors if f.id == "frid_classes"), None)
        assert frid_factor is not None
        assert frid_factor.points <= 16  # cap enforced

    def test_prn_decay(self, cfg, now):
        p = _empty_patient()

        # Just administered — should have points
        p.med_administrations = [
            MedAdmin("lorazepam", "141448", is_prn_sedative_opioid=True,
                     administered_at=now - timedelta(minutes=30))
        ]
        result_recent = score_patient(p, now, cfg)
        recent_pts = next((f.points for f in result_recent.factors if f.id == "prn_sedative_opioid"), 0)

        # 5 hours ago — should have fewer points
        p.med_administrations = [
            MedAdmin("lorazepam", "141448", is_prn_sedative_opioid=True,
                     administered_at=now - timedelta(hours=5))
        ]
        result_old = score_patient(p, now, cfg)
        old_pts = next((f.points for f in result_old.factors if f.id == "prn_sedative_opioid"), 0)

        assert recent_pts > old_pts

    def test_prn_expired(self, cfg, now):
        p = _empty_patient()
        p.med_administrations = [
            MedAdmin("lorazepam", "141448", is_prn_sedative_opioid=True,
                     administered_at=now - timedelta(hours=7))
        ]
        result = score_patient(p, now, cfg)
        assert "prn_sedative_opioid" not in [f.id for f in result.factors]

    def test_glucose_low(self, cfg, now):
        p = _empty_patient()
        p.labs = [Observation("2339-0", 62.0, "mg/dL", now - timedelta(hours=2), "laboratory")]
        result = score_patient(p, now, cfg)
        assert "glucose_low" in [f.id for f in result.factors]

    def test_diuretic_decay(self, cfg, now):
        p = _empty_patient()
        p.med_administrations = [
            MedAdmin("furosemide", "202991", is_diuretic=True, administered_at=now - timedelta(hours=3))
        ]
        r1 = score_patient(p, now, cfg)
        pts_3h = next((f.points for f in r1.factors if f.id == "diuretic_admin"), 0)

        p.med_administrations = [
            MedAdmin("furosemide", "202991", is_diuretic=True, administered_at=now - timedelta(hours=7))
        ]
        r2 = score_patient(p, now, cfg)
        pts_7h = next((f.points for f in r2.factors if f.id == "diuretic_admin"), 0)

        assert pts_3h > pts_7h

    def test_tethers(self, cfg, now):
        p = _empty_patient()
        p.devices = {"iv_pole", "foley", "telemetry"}
        result = score_patient(p, now, cfg)
        assert "tethers" in [f.id for f in result.factors]

    def test_no_factors_low_risk(self, cfg, now):
        p = _empty_patient(age=30)
        result = score_patient(p, now, cfg)
        assert result.fls < 25
        assert result.tier == Tier.ONE


class TestISSFactors:
    def test_anticoagulant(self, cfg, now):
        p = _empty_patient()
        p.active_medications = [MedOrder("apixaban", "1364430", is_anticoagulant=True)]
        result = score_patient(p, now, cfg)
        assert "anticoagulant" in [f.id for f in result.factors]

    def test_inr_high(self, cfg, now):
        p = _empty_patient()
        p.labs = [Observation("6301-6", 3.5, "", now - timedelta(hours=2), "laboratory")]
        result = score_patient(p, now, cfg)
        assert "inr_high" in [f.id for f in result.factors]

    def test_osteoporosis(self, cfg, now):
        p = _empty_patient(sex=Sex.FEMALE)
        p.diagnoses = ["M81.0"]
        result = score_patient(p, now, cfg)
        assert "osteoporosis" in [f.id for f in result.factors]

    def test_dexa_osteoporosis(self, cfg, now):
        p = _empty_patient()
        p.labs = [Observation("38263-0", -2.8, "T-score", now - timedelta(days=30), "laboratory")]
        result = score_patient(p, now, cfg)
        assert "osteoporosis" in [f.id for f in result.factors]

    def test_platelets_low(self, cfg, now):
        p = _empty_patient()
        p.labs = [Observation("777-3", 40.0, "k/μL", now - timedelta(hours=6), "laboratory")]
        result = score_patient(p, now, cfg)
        assert "platelets_low" in [f.id for f in result.factors]


class TestTierAssignment:
    def test_tier_matrix(self, cfg, now):
        # Low FLS + Low ISS → Tier 1
        p = _empty_patient(age=30)
        result = score_patient(p, now, cfg)
        assert result.tier == Tier.ONE

    def test_high_fls_high_iss_is_tier5(self, cfg, now):
        p = _empty_patient(age=88, sex=Sex.FEMALE)
        p.events = [ClinicalEvent("fall_this_admission", "", "", "", now - timedelta(hours=2), "FallEvent")]
        p.diagnoses = ["M81.0", "Z87.39", "F03.90"]
        p.active_medications = [
            MedOrder("apixaban", "1364430", is_anticoagulant=True),
            MedOrder("lorazepam", "141448", frid_classes=["benzodiazepine"], anticholinergic_burden=1),
        ]
        p.med_administrations = [
            MedAdmin("lorazepam", "141448", is_prn_sedative_opioid=True,
                     administered_at=now - timedelta(hours=1))
        ]
        p.assessments = [
            Observation("55752-0", "positive", "", now - timedelta(hours=2), "survey"),
            Observation("55755-3", "assist", "", now - timedelta(hours=4), "survey"),
        ]
        p.labs = [
            Observation("1751-7", 2.5, "g/dL", now - timedelta(hours=6), "laboratory"),
        ]
        p.bmi = 17.0
        result = score_patient(p, now, cfg)
        assert result.tier == Tier.FIVE

    def test_ehi_is_fls_times_iss_over_100(self, cfg, now):
        p = _empty_patient(age=88, sex=Sex.FEMALE)
        p.diagnoses = ["M81.0"]
        p.active_medications = [MedOrder("apixaban", "1364430", is_anticoagulant=True)]
        result = score_patient(p, now, cfg)
        expected_ehi = result.fls * result.iss / 100
        assert abs(result.ehi - expected_ehi) < 0.1

    def test_scores_capped_at_100(self, cfg, now):
        """Pile on every factor — scores must never exceed 100."""
        p = _empty_patient(age=90, sex=Sex.FEMALE)
        p.events = [
            ClinicalEvent("fall_this_admission", "", "", "", now - timedelta(hours=2), "FallEvent"),
            ClinicalEvent("fall_prior", "", "", "", now - timedelta(days=30), "FallEvent"),
            ClinicalEvent("orthostatic_drop", "", "", "", now - timedelta(hours=12), "Observation"),
            ClinicalEvent("chronic_glucocorticoids", "", "", "", now - timedelta(days=100), "Event"),
        ]
        p.diagnoses = ["M81.0", "Z87.39", "F03.90", "G20", "R32", "N18.6", "I48.91", "E21.0"]
        p.active_medications = [
            MedOrder("apixaban", "1364430", is_anticoagulant=True),
            MedOrder("aspirin", "1191", is_antiplatelet=True),
            MedOrder("clopidogrel", "309362", is_antiplatelet=True),
            MedOrder("lorazepam", "141448", frid_classes=["benzodiazepine"], anticholinergic_burden=2),
            MedOrder("oxycodone", "1049502", frid_classes=["opioid"]),
            MedOrder("haloperidol", "5521", frid_classes=["antipsychotic"], anticholinergic_burden=2),
            MedOrder("amitriptyline", "2404", frid_classes=["antidepressant"], anticholinergic_burden=3,
                     is_bone_weakening=True),
        ]
        p.med_administrations = [
            MedAdmin("lorazepam", "141448", is_prn_sedative_opioid=True,
                     administered_at=now - timedelta(minutes=45))
        ]
        p.labs = [
            Observation("2339-0", 55.0, "mg/dL", now - timedelta(hours=2), "laboratory"),
            Observation("2951-2", 125.0, "mEq/L", now, "laboratory"),
            Observation("718-7", 7.5, "g/dL", now - timedelta(hours=6), "laboratory"),
            Observation("6301-6", 4.0, "", now - timedelta(hours=8), "laboratory"),
            Observation("777-3", 35.0, "k/μL", now - timedelta(hours=6), "laboratory"),
            Observation("1751-7", 2.3, "g/dL", now - timedelta(hours=6), "laboratory"),
        ]
        p.assessments = [
            Observation("55752-0", "positive", "", now - timedelta(hours=3), "survey"),
            Observation("72461-0", 2, "", now - timedelta(hours=2), "survey"),
            Observation("74771-0", 15, "", now - timedelta(hours=2), "survey"),
            Observation("55755-3", "assist", "", now - timedelta(hours=8), "survey"),
        ]
        p.bmi = 16.0
        p.devices = {"iv_pole", "foley", "telemetry", "scd", "o2_tubing", "drain"}
        result = score_patient(p, now, cfg)
        assert result.fls <= 100
        assert result.iss_bone <= 100
        assert result.iss_bleed <= 100
        assert result.iss <= 100
        assert result.ehi <= 100


class TestScoreReproducibility:
    def test_deterministic(self, cfg, now):
        p = _empty_patient(age=75, sex=Sex.FEMALE)
        p.diagnoses = ["M81.0", "I48.91"]
        p.active_medications = [MedOrder("warfarin", "11289", is_anticoagulant=True)]
        r1 = score_patient(p, now, cfg)
        r2 = score_patient(p, now, cfg)
        assert r1.fls == r2.fls
        assert r1.iss == r2.iss
        assert r1.tier == r2.tier
