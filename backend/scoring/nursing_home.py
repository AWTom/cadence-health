"""Nursing home scoring (scoring mechanics v0.2, section 3) — pure functions, no I/O.

Fall Score: 7-item Morse-analog built on MDS + eMAR data.
Injury: FRAiL-Points bone component, banded by facility percentile, plus a bleed level.
Care Level: Fall level x Injury level grid. EHI = Fall Score x bone percentile / 100.

Bone levels are relative to the facility, so scoring is done per unit (score_unit),
not per resident.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import Evidence, Factor, ScoringConfig

LEVELS = ("Low", "Medium", "High")

# Rows = Fall level, cols = Injury level (Low, Medium, High)
CARE_GRID = [
    [1, 2, 3],
    [2, 3, 4],
    [3, 4, 5],
]


@dataclass
class Med:
    name: str
    classes: set[str] = field(default_factory=set)   # e.g. {"benzodiazepine"}, {"ssri", "antidepressant"}
    started_at: datetime | None = None
    dose_increased_at: datetime | None = None
    last_given_at: datetime | None = None


@dataclass
class ResidentState:
    """MDS-shaped resident record. Enum-like fields use the keys in scoring_config.yaml."""
    patient_id: str
    age: int
    female: bool
    mds_assessed_at: datetime | None = None
    fall_dates: list[datetime] = field(default_factory=list)          # incident log / MDS J
    fall_mobility: str = "steady"        # steady | aid_or_supervision | needs_help_gets_up_alone | cannot_stand
    walking: str = "independent"         # GG walk in room: independent | limited | extensive | total
    transfers: str = "independent"       # GG transfers: independent | limited | extensive | total
    adl: str = "independent"             # independent | extensive_1 | extensive_2 | dependent | total
    cognition: str = "intact"            # BIMS: intact | moderate | severe
    forgets_limits: bool = False
    wanders: bool = False                # also covers restless behaviour (MDS E)
    easily_distracted: bool = False
    bladder: str = "continent"           # continent | frequent | total
    urgency: bool = False
    dizziness_orthostatic_or_vision: bool = False
    diabetes: bool = False
    osteoarthritis: bool = False
    pressure_ulcer: bool = False
    prior_brain_bleed: bool = False
    bmi: float | None = None
    meds: list[Med] = field(default_factory=list)
    acute_changes: list[tuple[str, datetime]] = field(default_factory=list)  # (label, when)
    fall_score_7d_ago: float | None = None


@dataclass
class NHScore:
    patient_id: str
    calculated_at: datetime
    fall_score: float
    fall_level: str
    bone_points: float
    bone_percentile: float
    bone_level: str
    bleed_level: str
    injury_level: str
    care_level: int
    ehi: float
    factors: list[Factor]
    config_version: str
    data_gaps: list[str] = field(default_factory=list)
    risk_rising: bool = False
    phenotype: str | None = None   # roadmap (section 7): populated later


def _fall_level(score: float, cfg: ScoringConfig) -> str:
    if score <= cfg.get("nursing_home", "levels", "low_max", default=24):
        return "Low"
    if score <= cfg.get("nursing_home", "levels", "medium_max", default=49):
        return "Medium"
    return "High"


def _has(r: ResidentState, cls: str) -> list[Med]:
    return [m for m in r.meds if cls in m.classes]


# ── Fall Score ────────────────────────────────────────────────────────────────

def calc_fall_factors(r: ResidentState, now: datetime, cfg: ScoringConfig) -> list[Factor]:
    fc = lambda *k, default=0: cfg.get("nursing_home", "fall", *k, default=default)  # noqa: E731
    factors: list[Factor] = []

    # 1. Recent fall
    if r.fall_dates:
        last = max(r.fall_dates)
        days = (now - last).days
        pts = fc("recent_fall", "within_30d") if days <= 30 else fc("recent_fall", "within_180d") if days <= 180 else 0
        if pts:
            factors.append(Factor("recent_fall", f"Fall {days} days ago", pts, "history", False,
                                  [Evidence("Incident log", "fall", timestamp=last)]))

    # 2. Walking and transfers
    pts = fc("mobility", r.fall_mobility)
    if pts:
        label = {"aid_or_supervision": "Walker, cane or supervision",
                 "needs_help_gets_up_alone": "Needs hands-on help but gets up alone"}.get(r.fall_mobility, r.fall_mobility)
        factors.append(Factor("mobility", label, pts, "mobility", r.fall_mobility == "needs_help_gets_up_alone",
                              [Evidence("MDS Section GG", r.fall_mobility)]))

    # 3. Thinking and judgment
    if r.cognition == "severe" or r.wanders:
        key, label = "severe_restless_or_wanders", "Severe cognitive impairment, restless or wanders"
    elif r.cognition == "moderate" or r.forgets_limits:
        key, label = "moderate_or_forgets_limits", "Moderate cognitive impairment or forgets limits"
    else:
        key = ""
    if key:
        factors.append(Factor("cognition", label, fc("cognition", key), "cognition", False,
                              [Evidence("BIMS (MDS C/E)", r.cognition)]))

    # 4. Fall-risk medicine classes (grouped)
    groups_map: dict = fc("fall_risk_classes", default={})
    groups: dict[str, list[str]] = {}
    for m in r.meds:
        for c in m.classes:
            if c in groups_map:
                groups.setdefault(groups_map[c], []).append(m.name)
    if groups:
        table = fc("fall_risk_med_points", default=[0, 5, 10, 15])
        pts = table[min(len(groups), len(table) - 1)]
        names = sorted({n for ns in groups.values() for n in ns})
        factors.append(Factor("fall_risk_meds", f"{len(groups)} fall-risk medicine class{'es' if len(groups) > 1 else ''}",
                              pts, "medications", True,
                              [Evidence("eMAR / orders", ", ".join(names))]))

    # 5. Recent change (last 7 days), capped
    since = now - timedelta(days=fc("recent_change", "window_days", default=7))
    change_pts, evidence = 0, []
    changed = [m for m in r.meds
               if set(m.classes) & set(groups_map)
               and any(t and t >= since for t in (m.started_at, m.dose_increased_at))]
    if changed:
        change_pts += fc("recent_change", "new_or_increased_drug")
        evidence += [Evidence("eMAR / orders", f"{m.name} new or increased",
                              timestamp=max(t for t in (m.started_at, m.dose_increased_at) if t)) for m in changed]
    acute = [(label, t) for label, t in r.acute_changes if t >= since]
    if acute:
        change_pts += fc("recent_change", "acute_illness")
        evidence += [Evidence("Orders / notes", label, timestamp=t) for label, t in acute]
    if change_pts:
        factors.append(Factor("recent_change", "Recent change (last 7 days)",
                              min(change_pts, fc("recent_change", "cap", default=20)), "recent_change", True, evidence))

    # 6. Bathroom urgency
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    given_today = [m for m in r.meds if m.classes & {"diuretic", "laxative"} and m.last_given_at and m.last_given_at >= today]
    if (r.urgency and r.fall_mobility != "cannot_stand") or given_today:
        ev = [Evidence("eMAR", f"{m.name} given", timestamp=m.last_given_at) for m in given_today] or \
             [Evidence("MDS Section H", "urgency or frequency")]
        factors.append(Factor("bathroom_urgency", "Bathroom urgency", fc("bathroom_urgency"), "toileting", True, ev))

    # 7. Dizziness, orthostatic drop or poor vision
    if r.dizziness_orthostatic_or_vision:
        factors.append(Factor("dizziness_vision", "Dizziness, orthostatic drop or poor vision",
                              fc("dizziness_orthostatic_vision"), "sensory", True,
                              [Evidence("Diagnoses / vitals / MDS B", "present")]))
    return factors


# ── Injury: bone (FRAiL-Points) ───────────────────────────────────────────────

def calc_bone_factors(r: ResidentState, cfg: ScoringConfig) -> tuple[list[Factor], list[str]]:
    bc = lambda *k, default=0: cfg.get("nursing_home", "bone", *k, default=default)  # noqa: E731
    factors: list[Factor] = []
    gaps: list[str] = []

    def add(fid: str, label: str, pts: float, source: str, value, modifiable: bool = False):
        if pts:
            factors.append(Factor(fid, label, pts, "bone", modifiable, [Evidence(source, value)]))

    add("bone_female", "Female", bc("female") if r.female else 0, "Demographics", "female")
    add("bone_walking", f"Walks in room ({r.walking})", bc("walking", r.walking), "MDS Section GG", r.walking)
    add("bone_transfers", f"Transfers ({r.transfers})", bc("transfers", r.transfers), "MDS Section GG", r.transfers)
    add("bone_adl", f"ADL hierarchy ({r.adl.replace('_', ' ')})", bc("adl", r.adl), "MDS ADL hierarchy", r.adl)
    add("bone_bladder", f"Bladder ({r.bladder})", bc("bladder", r.bladder), "MDS Section H", r.bladder)

    if r.bmi is None:
        gaps.append("BMI missing")
    else:
        pts = next(p for lo, p in bc("bmi_bands", default=[[0, 0]]) if r.bmi >= lo)
        add("bone_bmi", f"BMI {r.bmi:.1f}", pts, "Vitals", round(r.bmi, 1), modifiable=r.bmi < 22)

    add("bone_cognition", f"Cognition ({r.cognition})", bc("cognition", r.cognition), "BIMS", r.cognition)
    add("bone_diabetes", "Diabetes (female)", bc("diabetes_female") if r.diabetes and r.female else 0, "Diagnoses", "diabetes")

    for cls, pts in bc("drug_classes", default={}).items():
        for m in _has(r, cls):
            add(f"bone_{cls}", f"{m.name} ({cls.replace('_', ' ')})", pts, "eMAR / orders", m.name, modifiable=True)

    add("bone_distracted", "Easily distracted", bc("easily_distracted") if r.easily_distracted else 0, "MDS Section C", "yes")
    add("bone_pressure_ulcer", "Pressure ulcer", bc("pressure_ulcer") if r.pressure_ulcer else 0, "MDS Section M", "yes")
    add("bone_osteoarthritis", "Osteoarthritis", bc("osteoarthritis") if r.osteoarthritis else 0, "Diagnoses", "yes")

    if bc("mode", default="injury") == "full":
        add("bone_previous_fall", "Previous fall", bc("previous_fall_full_mode") if r.fall_dates else 0, "Incident log", "yes")
        add("bone_wandering", "Wandering", bc("wandering_full_mode") if r.wanders else 0, "MDS Section E", "yes")
    return factors, gaps


# ── Injury: bleed ─────────────────────────────────────────────────────────────

def calc_bleed(r: ResidentState, now: datetime, cfg: ScoringConfig) -> tuple[str, list[Factor]]:
    anticoag = _has(r, "anticoagulant")
    dual_antiplatelet = len(_has(r, "antiplatelet")) >= 2
    recent_days = cfg.get("nursing_home", "bleed", "recent_fall_days", default=30)
    recent_fall = any((now - d).days <= recent_days for d in r.fall_dates)

    factors = [Factor("bleed_anticoagulant", f"Anticoagulant ({m.name})", 0, "bleed", False,
                      [Evidence("eMAR / orders", m.name)]) for m in anticoag]
    if dual_antiplatelet:
        factors.append(Factor("bleed_dual_antiplatelet", "Dual antiplatelet therapy", 0, "bleed", True,
                              [Evidence("eMAR / orders", ", ".join(m.name for m in _has(r, "antiplatelet")))]))
    if r.prior_brain_bleed:
        factors.append(Factor("bleed_prior_brain_bleed", "Prior brain bleed", 0, "bleed", False,
                              [Evidence("Diagnoses", "intracranial hemorrhage")]))

    if (anticoag and recent_fall) or dual_antiplatelet or r.prior_brain_bleed:
        return "High", factors
    if anticoag:
        return "Medium", factors
    return "Low", factors


# ── Unit scoring ──────────────────────────────────────────────────────────────

def _percentiles(values: list[float]) -> list[float]:
    """Mid-rank percentile of each value within the list (0-100)."""
    n = len(values)
    return [100.0 * (sum(w < v for w in values) + 0.5 * sum(w == v for w in values)) / n for v in values]


def score_unit(residents: list[ResidentState], now: datetime, cfg: ScoringConfig) -> list[NHScore]:
    """Score every resident in a facility. Bone levels are banded by facility percentile."""
    if not residents:
        return []
    nh = lambda *k, default=None: cfg.get("nursing_home", *k, default=default)  # noqa: E731

    fall_parts = [calc_fall_factors(r, now, cfg) for r in residents]
    bone_parts = [calc_bone_factors(r, cfg) for r in residents]
    bone_points = [max(0.0, sum(f.points for f in fs)) for fs, _ in bone_parts]
    percentiles = _percentiles(bone_points)

    high_min = nh("bone", "percentile_bands", "high_min", default=80)
    medium_min = nh("bone", "percentile_bands", "medium_min", default=50)
    overdue_days = nh("mds_overdue_days", default=92)
    penalty = cfg.get("missing_data_penalty", default=3)

    results = []
    for r, fall_factors, (bone_factors, gaps), pts, pct in zip(residents, fall_parts, bone_parts, bone_points, percentiles):
        gaps = list(gaps)
        if r.mds_assessed_at is None or (now - r.mds_assessed_at).days > overdue_days:
            gaps.append("MDS assessment overdue")
            fall_factors = fall_factors + [Factor("data_gap", "MDS assessment overdue", penalty, "data_gap", True,
                                                  [Evidence("MDS", "overdue", timestamp=r.mds_assessed_at)])]

        fall = min(100.0, sum(f.points for f in fall_factors))
        fall_level = _fall_level(fall, cfg)
        bone_level = "High" if pct >= high_min else "Medium" if pct >= medium_min else "Low"
        bleed_level, bleed_factors = calc_bleed(r, now, cfg)
        injury_level = max(bone_level, bleed_level, key=LEVELS.index)
        care_level = CARE_GRID[LEVELS.index(fall_level)][LEVELS.index(injury_level)]

        # fall_score_7d_ago is the stored snapshot from risk_rising.window_days ago
        rising = (r.fall_score_7d_ago is not None
                  and fall - r.fall_score_7d_ago >= nh("risk_rising", "points", default=15))

        results.append(NHScore(
            patient_id=r.patient_id,
            calculated_at=now,
            fall_score=round(fall, 1),
            fall_level=fall_level,
            bone_points=round(pts, 1),
            bone_percentile=round(pct, 1),
            bone_level=bone_level,
            bleed_level=bleed_level,
            injury_level=injury_level,
            care_level=care_level,
            ehi=round(fall * pct / 100.0, 1),
            factors=fall_factors + bone_factors + bleed_factors,
            config_version=cfg.version,
            data_gaps=gaps,
            risk_rising=rising,
        ))
    return results
