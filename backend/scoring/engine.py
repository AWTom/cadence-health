"""Core scoring engine — pure function, no I/O, fully deterministic."""
from __future__ import annotations
from datetime import datetime

from .models import PatientState, ScoringConfig, ScoreResult, Tier
from .fls import calc_fls
from .iss import calc_iss_bone, calc_iss_bleed


def _tier(fls: float, iss: float, cfg: ScoringConfig) -> Tier:
    low_max = cfg.get("tier_bands", "low_max", default=24)
    mod_max = cfg.get("tier_bands", "moderate_max", default=49)

    def band(score: float) -> int:  # 0=low, 1=moderate, 2=high
        if score <= low_max:
            return 0
        if score <= mod_max:
            return 1
        return 2

    fb, ib = band(fls), band(iss)
    # Tier table from spec: rows=FLS (high→low), cols=ISS (low→high)
    table = [
        [1, 2, 3],  # FLS low
        [2, 3, 4],  # FLS moderate
        [3, 4, 5],  # FLS high
    ]
    return Tier(table[fb][ib])


def score_patient(state: PatientState, now: datetime, cfg: ScoringConfig) -> ScoreResult:
    """
    Pure function. Returns FLS, ISS, EHI, tier, and all contributing factors.
    PatientState must contain all ClinicalEvents for the encounter.
    """
    fls_factors = calc_fls(state, now, cfg)
    bone_factors = calc_iss_bone(state, now, cfg)
    bleed_factors = calc_iss_bleed(state, now, cfg)

    fls = min(100.0, sum(f.points for f in fls_factors))
    iss_bone = min(100.0, sum(f.points for f in bone_factors))
    iss_bleed = min(100.0, sum(f.points for f in bleed_factors))

    minor_weight = cfg.get("iss", "combined_minor_weight", default=0.25)
    iss = min(100.0, max(iss_bone, iss_bleed) + minor_weight * min(iss_bone, iss_bleed))

    ehi = fls * iss / 100.0

    tier = _tier(fls, iss, cfg)
    all_factors = fls_factors + bone_factors + bleed_factors

    return ScoreResult(
        patient_id=state.patient_id,
        encounter_id=state.encounter_id,
        calculated_at=now,
        fls=round(fls, 1),
        iss_bone=round(iss_bone, 1),
        iss_bleed=round(iss_bleed, 1),
        iss=round(iss, 1),
        ehi=round(ehi, 1),
        tier=tier,
        factors=all_factors,
        config_version=cfg.version,
    )
