"""Injury Severity Score (ISS) factor calculators — bone and bleed sub-scores."""
from __future__ import annotations
from datetime import datetime, timedelta

from .models import Factor, Evidence, PatientState, ScoringConfig, Sex, Observation


def _latest_obs(obs_list: list[Observation], loinc: str) -> Observation | None:
    candidates = [o for o in obs_list if o.loinc == loinc]
    return max(candidates, key=lambda o: o.timestamp) if candidates else None


def calc_iss_bone(state: PatientState, now: datetime, cfg: ScoringConfig) -> list[Factor]:
    factors: list[Factor] = []

    # Osteoporosis
    dexa_obs = _latest_obs(state.labs, "38263-0")  # DEXA T-score
    has_osteoporosis_dx = any(d.startswith("M81") for d in state.diagnoses)
    has_osteopenia_dx = any(d.startswith("M85.8") or d.startswith("M85.0") for d in state.diagnoses)

    if has_osteoporosis_dx or (dexa_obs and float(dexa_obs.value) <= -2.5):
        evidence = [Evidence("Condition", "Osteoporosis")]
        if dexa_obs:
            evidence.append(Evidence("Observation/DEXA", dexa_obs.value, "T-score", dexa_obs.timestamp))
        factors.append(Factor(
            id="osteoporosis", label="Osteoporosis (or DEXA T-score ≤ −2.5)",
            points=cfg.get("iss", "bone", "osteoporosis", default=20),
            category="bone", modifiable=False, evidence=evidence,
        ))
    elif has_osteopenia_dx or (dexa_obs and -2.5 < float(dexa_obs.value) <= -1.0):
        factors.append(Factor(
            id="osteopenia", label="Osteopenia (T-score −1 to −2.5)",
            points=cfg.get("iss", "bone", "osteopenia", default=8),
            category="bone", modifiable=False,
        ))

    # Prior fragility fracture
    fragility_codes = {"M80", "S12", "S22", "S32", "S52", "S72"}  # vertebral, hip, wrist, humerus
    if any(d[:3] in fragility_codes or d[:4] in fragility_codes for d in state.diagnoses):
        factors.append(Factor(
            id="prior_fragility_fracture", label="Prior fragility fracture",
            points=cfg.get("iss", "bone", "prior_fragility_fracture", default=20),
            category="bone", modifiable=False,
        ))

    # Osteoporosis therapy (marker of known disease)
    if any(m.is_osteoporosis_therapy for m in state.active_medications):
        factors.append(Factor(
            id="osteoporosis_therapy", label="On osteoporosis therapy",
            points=cfg.get("iss", "bone", "osteoporosis_therapy", default=5),
            category="bone", modifiable=False,
        ))

    # Chronic glucocorticoids
    if any(e.type == "chronic_glucocorticoids" for e in state.events):
        factors.append(Factor(
            id="chronic_glucocorticoids", label="Chronic glucocorticoids (≥ 5 mg/day ≥ 3 months)",
            points=cfg.get("iss", "bone", "chronic_glucocorticoids", default=10),
            category="bone", modifiable=True,
        ))

    # Bone-weakening drugs
    bone_weakening_classes_seen: set[str] = set()
    for med in state.active_medications:
        if med.is_bone_weakening:
            bone_weakening_classes_seen.add(med.drug_name)
    bw_cap = cfg.get("iss", "bone", "bone_weakening_drug_cap", default=8)
    bw_pts_each = cfg.get("iss", "bone", "bone_weakening_drug_per_class", default=4)
    if bone_weakening_classes_seen:
        pts = min(len(bone_weakening_classes_seen) * bw_pts_each, bw_cap)
        factors.append(Factor(
            id="bone_weakening_drugs", label="Bone-weakening medications",
            points=pts, category="bone", modifiable=True,
            evidence=[Evidence("MedicationRequest", ", ".join(sorted(bone_weakening_classes_seen)))],
        ))

    # Age ≥ 80
    if state.age >= 80:
        factors.append(Factor(
            id="age_80_bone", label="Age ≥ 80",
            points=cfg.get("iss", "bone", "age_80_plus", default=10),
            category="bone", modifiable=False,
            evidence=[Evidence("Patient", state.age, "years")],
        ))

    # Female sex
    if state.sex == Sex.FEMALE:
        factors.append(Factor(
            id="female_sex", label="Female sex",
            points=cfg.get("iss", "bone", "female_sex", default=5),
            category="bone", modifiable=False,
        ))

    # Low BMI
    bmi_thresh = cfg.get("iss", "bone", "bmi_low_threshold", default=18.5)
    if state.bmi and state.bmi < bmi_thresh:
        factors.append(Factor(
            id="bmi_low", label=f"BMI < {bmi_thresh}",
            points=cfg.get("iss", "bone", "bmi_low_points", default=10),
            category="bone", modifiable=False,
            evidence=[Evidence("Observation/BMI", round(state.bmi, 1))],
        ))

    # Weight loss ≥ 5% in 30 days
    wl_pct = cfg.get("iss", "bone", "weight_loss_pct_threshold", default=5)
    if state.weight_kg and state.weight_30d_ago_kg and state.weight_30d_ago_kg > 0:
        pct_lost = (state.weight_30d_ago_kg - state.weight_kg) / state.weight_30d_ago_kg * 100
        if pct_lost >= wl_pct:
            factors.append(Factor(
                id="weight_loss", label=f"Weight loss ≥ {wl_pct}% in 30 days",
                points=cfg.get("iss", "bone", "weight_loss_points", default=5),
                category="bone", modifiable=False,
                evidence=[Evidence("Observation/Weight", f"{pct_lost:.1f}% loss")],
            ))

    # Albumin < 3.0
    albumin_thresh = cfg.get("iss", "bone", "albumin_low_threshold", default=3.0)
    albumin_obs = _latest_obs(state.labs, "1751-7")
    if albumin_obs and float(albumin_obs.value) < albumin_thresh:
        factors.append(Factor(
            id="albumin_low", label=f"Albumin < {albumin_thresh} g/dL",
            points=cfg.get("iss", "bone", "albumin_low_points", default=5),
            category="bone", modifiable=True,
            evidence=[Evidence("Observation/Albumin", albumin_obs.value, "g/dL", albumin_obs.timestamp)],
        ))

    # CKD stage 4–5 / dialysis
    if any(d.startswith(("N18.4", "N18.5", "N18.6", "Z99.2")) for d in state.diagnoses):
        factors.append(Factor(
            id="ckd_severe", label="CKD stage 4–5 or dialysis",
            points=cfg.get("iss", "bone", "ckd_stage_4_5", default=8),
            category="bone", modifiable=False,
        ))

    # Hyperparathyroidism
    if any(d.startswith("E21") for d in state.diagnoses):
        factors.append(Factor(
            id="hyperparathyroidism", label="Hyperparathyroidism",
            points=cfg.get("iss", "bone", "hyperparathyroidism", default=5),
            category="bone", modifiable=True,
        ))

    # Vitamin D < 20 ng/mL
    vitd_thresh = cfg.get("iss", "bone", "vitd_low_threshold", default=20)
    vitd_obs = _latest_obs(state.labs, "62292-8")
    if vitd_obs and float(vitd_obs.value) < vitd_thresh:
        factors.append(Factor(
            id="vitd_low", label=f"Vitamin D < {vitd_thresh} ng/mL",
            points=cfg.get("iss", "bone", "vitd_low_points", default=4),
            category="bone", modifiable=True,
            evidence=[Evidence("Observation/VitD", vitd_obs.value, "ng/mL", vitd_obs.timestamp)],
        ))

    # Bone metastases / multiple myeloma
    if any(d.startswith(("C79.5", "C90")) for d in state.diagnoses):
        factors.append(Factor(
            id="bone_metastases", label="Bone metastases or multiple myeloma",
            points=cfg.get("iss", "bone", "bone_metastases_myeloma", default=15),
            category="bone", modifiable=False,
        ))

    # Recent joint replacement / fracture fixation this admission
    if any(e.type == "joint_replacement" for e in state.events):
        factors.append(Factor(
            id="recent_joint_replacement", label="Recent joint replacement / fracture fixation (this admission)",
            points=cfg.get("iss", "bone", "recent_joint_replacement", default=10),
            category="bone", modifiable=False,
        ))

    # Clinical Frailty Scale ≥ 6
    cfs_thresh = cfg.get("iss", "bone", "frailty_scale_threshold", default=6)
    cfs_obs = _latest_obs(state.assessments, "93677-4")
    if cfs_obs and float(cfs_obs.value) >= cfs_thresh:
        factors.append(Factor(
            id="frailty", label=f"Clinical Frailty Scale ≥ {cfs_thresh}",
            points=cfg.get("iss", "bone", "frailty_scale_points", default=10),
            category="bone", modifiable=False,
            evidence=[Evidence("Observation/CFS", cfs_obs.value, timestamp=cfs_obs.timestamp)],
        ))

    return factors


def calc_iss_bleed(state: PatientState, now: datetime, cfg: ScoringConfig) -> list[Factor]:
    factors: list[Factor] = []

    # Therapeutic anticoagulant
    if any(m.is_anticoagulant for m in state.active_medications):
        meds = [m.drug_name for m in state.active_medications if m.is_anticoagulant]
        factors.append(Factor(
            id="anticoagulant", label="Therapeutic anticoagulant",
            points=cfg.get("iss", "bleed", "therapeutic_anticoagulant", default=15),
            category="bleed", modifiable=True,
            evidence=[Evidence("MedicationRequest", ", ".join(meds))],
        ))

    # INR > 3
    inr_thresh = cfg.get("iss", "bleed", "inr_high_threshold", default=3)
    inr_obs = _latest_obs(state.labs, "6301-6")
    if inr_obs and float(inr_obs.value) > inr_thresh:
        factors.append(Factor(
            id="inr_high", label=f"INR > {inr_thresh}",
            points=cfg.get("iss", "bleed", "inr_high_points", default=10),
            category="bleed", modifiable=True,
            evidence=[Evidence("Observation/INR", inr_obs.value, timestamp=inr_obs.timestamp)],
        ))

    # Dual antiplatelet
    antiplatelet_meds = [m for m in state.active_medications if m.is_antiplatelet]
    if len(antiplatelet_meds) >= 2:
        factors.append(Factor(
            id="dual_antiplatelet", label="Dual antiplatelet therapy",
            points=cfg.get("iss", "bleed", "dual_antiplatelet", default=8),
            category="bleed", modifiable=True,
            evidence=[Evidence("MedicationRequest", ", ".join(m.drug_name for m in antiplatelet_meds[:2]))],
        ))

    # Platelets < 50k
    plt_thresh = cfg.get("iss", "bleed", "platelets_low_threshold", default=50)
    plt_obs = _latest_obs(state.labs, "777-3")
    if plt_obs and float(plt_obs.value) < plt_thresh:
        factors.append(Factor(
            id="platelets_low", label=f"Platelets < {plt_thresh}k",
            points=cfg.get("iss", "bleed", "platelets_low_points", default=12),
            category="bleed", modifiable=False,
            evidence=[Evidence("Observation/Platelets", plt_obs.value, "k/μL", plt_obs.timestamp)],
        ))

    # Prior craniotomy / missing bone flap
    if any(d.startswith(("Z96.6", "Z87.39")) or e.type == "craniotomy"
           for d in state.diagnoses for e in state.events):
        factors.append(Factor(
            id="prior_craniotomy", label="Prior craniotomy / missing bone flap",
            points=cfg.get("iss", "bleed", "prior_craniotomy", default=20),
            category="bleed", modifiable=False,
        ))

    return factors
