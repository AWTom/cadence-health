"""Fall Likelihood Score (FLS) factor calculators."""
from __future__ import annotations
import math
from datetime import datetime, timedelta

from .models import Factor, Evidence, PatientState, ScoringConfig, Observation, MedAdmin


def _latest_obs(obs_list: list[Observation], loinc: str, window_hours: float | None = None, now: datetime | None = None) -> Observation | None:
    candidates = [o for o in obs_list if o.loinc == loinc]
    if window_hours and now:
        cutoff = now - timedelta(hours=window_hours)
        candidates = [o for o in candidates if o.timestamp >= cutoff]
    return max(candidates, key=lambda o: o.timestamp) if candidates else None


def _decay_fraction(administered_at: datetime, decay_hours: float, now: datetime) -> float:
    elapsed = (now - administered_at).total_seconds() / 3600
    return max(0.0, 1.0 - elapsed / decay_hours)


def calc_fls(state: PatientState, now: datetime, cfg: ScoringConfig) -> list[Factor]:
    factors: list[Factor] = []

    # --- History ---
    if any(e.type == "fall_this_admission" for e in state.events):
        factors.append(Factor(
            id="fall_this_admission",
            label="Fall during this admission",
            points=cfg.get("fls", "history", "fall_this_admission", default=25),
            category="history", modifiable=False,
            evidence=[Evidence("FallEvent", "documented", timestamp=now)],
        ))

    cutoff_6m = now - timedelta(days=180)
    if any(e.type == "fall_prior" and e.timestamp >= cutoff_6m for e in state.events):
        factors.append(Factor(
            id="fall_past_6_months",
            label="Fall in past 6 months",
            points=cfg.get("fls", "history", "fall_past_6_months", default=15),
            category="history", modifiable=False,
        ))

    # --- Age ---
    age = state.age
    if age >= 85:
        pts = cfg.get("fls", "age", "age_85_plus", default=15)
        label = "Age ≥ 85"
    elif age >= 75:
        pts = cfg.get("fls", "age", "age_75_84", default=10)
        label = "Age 75–84"
    elif age >= 65:
        pts = cfg.get("fls", "age", "age_65_74", default=5)
        label = "Age 65–74"
    else:
        pts = 0
        label = ""
    if pts:
        factors.append(Factor(id="age", label=label, points=pts, category="age", modifiable=False,
                               evidence=[Evidence("Patient", age, "years")]))

    # --- Cognition ---
    cam_window = cfg.get("fls", "cognition", "cam_window_hours", default=24)
    cam_obs = _latest_obs(state.assessments, "55752-0", window_hours=cam_window, now=now)
    if cam_obs and str(cam_obs.value).lower() in ("positive", "1", "yes", "true"):
        factors.append(Factor(
            id="cam_positive", label="Delirium (CAM positive)",
            points=cfg.get("fls", "cognition", "cam_positive", default=15),
            category="cognition", modifiable=True,
            evidence=[Evidence("Observation/CAM", cam_obs.value, timestamp=cam_obs.timestamp)],
        ))

    if any(d.startswith(("F00", "F01", "F02", "F03", "G30", "G31")) for d in state.diagnoses):
        factors.append(Factor(id="dementia", label="Dementia diagnosis",
                               points=cfg.get("fls", "cognition", "dementia", default=8),
                               category="cognition", modifiable=False))

    rass_window = cfg.get("fls", "cognition", "rass_window_hours", default=12)
    rass_obs = _latest_obs(state.assessments, "72461-0", window_hours=rass_window, now=now)
    if rass_obs and rass_obs.value not in (0, "0"):
        factors.append(Factor(
            id="rass_nonzero", label="RASS ≠ 0 (agitated or sedated)",
            points=cfg.get("fls", "cognition", "rass_nonzero", default=5),
            category="cognition", modifiable=True,
            evidence=[Evidence("Observation/RASS", rass_obs.value, timestamp=rass_obs.timestamp)],
        ))

    ciwa_window = cfg.get("fls", "cognition", "ciwa_window_hours", default=12)
    ciwa_obs = _latest_obs(state.assessments, "74771-0", window_hours=ciwa_window, now=now)
    ciwa_threshold = cfg.get("fls", "cognition", "ciwa_threshold", default=10)
    if ciwa_obs and isinstance(ciwa_obs.value, (int, float)) and ciwa_obs.value >= ciwa_threshold:
        factors.append(Factor(
            id="ciwa_elevated", label=f"Alcohol withdrawal (CIWA ≥ {ciwa_threshold})",
            points=cfg.get("fls", "cognition", "ciwa_points", default=10),
            category="cognition", modifiable=False,
            evidence=[Evidence("Observation/CIWA", ciwa_obs.value, timestamp=ciwa_obs.timestamp)],
        ))

    # --- Medications (FRIDs) ---
    frid_classes_seen: set[str] = set()
    anticholinergic_burden = 0
    for med in state.active_medications:
        frid_classes_seen.update(med.frid_classes)
        anticholinergic_burden += med.anticholinergic_burden

    frid_pts_per_class = cfg.get("fls", "medications", "frid_class_points", default=4)
    frid_cap = cfg.get("fls", "medications", "frid_cap", default=16)
    if frid_classes_seen:
        pts = min(len(frid_classes_seen) * frid_pts_per_class, frid_cap)
        factors.append(Factor(
            id="frid_classes", label=f"Fall-risk drugs ({len(frid_classes_seen)} class{'es' if len(frid_classes_seen)>1 else ''})",
            points=pts, category="medications", modifiable=True,
            evidence=[Evidence("MedicationRequest", ", ".join(sorted(frid_classes_seen)))],
        ))

    new_frid_window = cfg.get("fls", "medications", "new_frid_window_hours", default=24)
    new_frids = [
        m for m in state.active_medications
        if m.dose_changed_at and m.dose_changed_at >= now - timedelta(hours=new_frid_window)
        and m.frid_classes
    ]
    if new_frids:
        factors.append(Factor(
            id="new_frid", label="New FRID started or dose increased (last 24h)",
            points=cfg.get("fls", "medications", "new_frid_points", default=8),
            category="medications", modifiable=True,
            evidence=[Evidence("MedicationRequest", m.drug_name, timestamp=m.dose_changed_at) for m in new_frids],
        ))

    prn_pts_base = cfg.get("fls", "medications", "prn_sedative_opioid_points", default=8)
    prn_decay_h = cfg.get("fls", "medications", "prn_decay_hours", default=6)
    prn_admins = [a for a in state.med_administrations if a.is_prn_sedative_opioid]
    if prn_admins:
        most_recent_prn = max(prn_admins, key=lambda a: a.administered_at)
        frac = _decay_fraction(most_recent_prn.administered_at, prn_decay_h, now)
        pts = prn_pts_base * frac
        if pts > 0.5:
            factors.append(Factor(
                id="prn_sedative_opioid", label="PRN sedative/opioid administered",
                points=round(pts, 1), category="medications", modifiable=False,
                evidence=[Evidence("MedicationAdministration", most_recent_prn.drug_name,
                                   timestamp=most_recent_prn.administered_at)],
            ))

    acb_threshold = cfg.get("fls", "medications", "anticholinergic_burden_threshold", default=3)
    if anticholinergic_burden >= acb_threshold:
        factors.append(Factor(
            id="anticholinergic_burden", label=f"Anticholinergic burden ≥ {acb_threshold}",
            points=cfg.get("fls", "medications", "anticholinergic_burden_points", default=6),
            category="medications", modifiable=True,
            evidence=[Evidence("MedicationRequest", f"ACB score {anticholinergic_burden}")],
        ))

    # --- Hemodynamics & metabolic ---
    ortho_window = cfg.get("fls", "hemodynamics", "orthostatic_window_hours", default=48)
    sbp_obs = [o for o in state.vitals if o.loinc == "8480-6" and o.timestamp >= now - timedelta(hours=ortho_window)]
    # Orthostatic: look for paired lying/standing readings — simplified: flag if explicitly coded
    ortho_events = [e for e in state.events if e.type == "orthostatic_drop" and e.timestamp >= now - timedelta(hours=ortho_window)]
    if ortho_events:
        factors.append(Factor(
            id="orthostatic_drop", label="Orthostatic BP drop",
            points=cfg.get("fls", "hemodynamics", "orthostatic_drop_points", default=8),
            category="hemodynamics", modifiable=True,
            evidence=[Evidence("Observation/BP", "SBP drop ≥20 or DBP drop ≥10", timestamp=ortho_events[-1].timestamp)],
        ))

    sbp_low_win = cfg.get("fls", "hemodynamics", "sbp_low_window_hours", default=12)
    sbp_low_thresh = cfg.get("fls", "hemodynamics", "sbp_low_threshold", default=90)
    sbp_recent = [o for o in state.vitals if o.loinc == "8480-6" and o.timestamp >= now - timedelta(hours=sbp_low_win)]
    if sbp_recent and min(float(o.value) for o in sbp_recent) < sbp_low_thresh:
        worst = min(sbp_recent, key=lambda o: float(o.value))
        factors.append(Factor(
            id="sbp_low", label=f"SBP < {sbp_low_thresh} mmHg",
            points=cfg.get("fls", "hemodynamics", "sbp_low_points", default=5),
            category="hemodynamics", modifiable=True,
            evidence=[Evidence("Observation/BP", worst.value, "mmHg", worst.timestamp)],
        ))

    glucose_win = cfg.get("fls", "hemodynamics", "glucose_window_hours", default=24)
    glucose_thresh = cfg.get("fls", "hemodynamics", "glucose_low_threshold", default=70)
    glucose_obs = [o for o in state.labs if o.loinc == "2339-0" and o.timestamp >= now - timedelta(hours=glucose_win)]
    if glucose_obs and min(float(o.value) for o in glucose_obs) < glucose_thresh:
        worst = min(glucose_obs, key=lambda o: float(o.value))
        factors.append(Factor(
            id="glucose_low", label=f"Glucose < {glucose_thresh} mg/dL",
            points=cfg.get("fls", "hemodynamics", "glucose_low_points", default=8),
            category="hemodynamics", modifiable=True,
            evidence=[Evidence("Observation/glucose", worst.value, "mg/dL", worst.timestamp)],
        ))

    sodium_thresh = cfg.get("fls", "hemodynamics", "sodium_low_threshold", default=130)
    sodium_obs = _latest_obs(state.labs, "2951-2")
    if sodium_obs and float(sodium_obs.value) < sodium_thresh:
        factors.append(Factor(
            id="sodium_low", label=f"Sodium < {sodium_thresh} mEq/L",
            points=cfg.get("fls", "hemodynamics", "sodium_low_points", default=5),
            category="hemodynamics", modifiable=True,
            evidence=[Evidence("Observation/Na", sodium_obs.value, "mEq/L", sodium_obs.timestamp)],
        ))

    hgb_thresh = cfg.get("fls", "hemodynamics", "hgb_low_threshold", default=8)
    hgb_obs = _latest_obs(state.labs, "718-7")
    if hgb_obs and float(hgb_obs.value) < hgb_thresh:
        factors.append(Factor(
            id="hgb_low", label=f"Hemoglobin < {hgb_thresh} g/dL",
            points=cfg.get("fls", "hemodynamics", "hgb_low_points", default=5),
            category="hemodynamics", modifiable=True,
            evidence=[Evidence("Observation/Hgb", hgb_obs.value, "g/dL", hgb_obs.timestamp)],
        ))

    # --- Mobility & neuro ---
    mobility_obs = _latest_obs(state.assessments, "55755-3")
    if mobility_obs and str(mobility_obs.value).lower() in ("assist", "dependent", "limited"):
        factors.append(Factor(
            id="mobility_assist", label="Requires assistance with mobility",
            points=cfg.get("fls", "mobility", "assistance_required", default=8),
            category="mobility", modifiable=True,
            evidence=[Evidence("Observation/Mobility", mobility_obs.value, timestamp=mobility_obs.timestamp)],
        ))

    neuro_dx = {"G20", "G35", "G60", "G80", "G83", "I69", "G54"}
    if any(d[:3] in neuro_dx or d[:4] in neuro_dx for d in state.diagnoses):
        factors.append(Factor(
            id="neuro_weakness", label="Lower-limb weakness / neurological condition",
            points=cfg.get("fls", "mobility", "neuro_weakness", default=6),
            category="mobility", modifiable=False,
        ))

    if any(d.startswith("Z89") for d in state.diagnoses):
        factors.append(Factor(
            id="amputation", label="Lower-limb amputation",
            points=cfg.get("fls", "mobility", "amputation", default=6),
            category="mobility", modifiable=False,
        ))

    vestibular_dx = {"H81", "R42"}
    if any(d[:3] in vestibular_dx for d in state.diagnoses):
        factors.append(Factor(
            id="vestibular", label="Vestibular disorder / vertigo",
            points=cfg.get("fls", "mobility", "vestibular", default=5),
            category="mobility", modifiable=False,
        ))

    # --- Toileting ---
    if any(d.startswith(("R32", "N39.3", "N39.4")) for d in state.diagnoses):
        factors.append(Factor(
            id="incontinence", label="Incontinence or urgency",
            points=cfg.get("fls", "toileting", "incontinence", default=6),
            category="toileting", modifiable=True,
        ))

    diuretic_pts = cfg.get("fls", "toileting", "diuretic_points", default=6)
    diuretic_decay_h = cfg.get("fls", "toileting", "diuretic_decay_hours", default=6)
    diuretic_admins = sorted([a for a in state.med_administrations if a.is_diuretic],
                              key=lambda a: a.administered_at)
    if diuretic_admins:
        most_recent = diuretic_admins[-1]
        frac = _decay_fraction(most_recent.administered_at, diuretic_decay_h, now)
        pts = diuretic_pts * frac
        if pts > 0.5:
            factors.append(Factor(
                id="diuretic_admin", label="Diuretic administered",
                points=round(pts, 1), category="toileting", modifiable=False,
                evidence=[Evidence("MedicationAdministration", most_recent.drug_name, timestamp=most_recent.administered_at)],
            ))

    laxative_pts = cfg.get("fls", "toileting", "laxative_points", default=6)
    laxative_decay_h = cfg.get("fls", "toileting", "laxative_decay_hours", default=8)
    laxative_admins = sorted([a for a in state.med_administrations if a.is_laxative],
                              key=lambda a: a.administered_at)
    if laxative_admins:
        most_recent = laxative_admins[-1]
        frac = _decay_fraction(most_recent.administered_at, laxative_decay_h, now)
        pts = laxative_pts * frac
        if pts > 0.5:
            factors.append(Factor(
                id="laxative_admin", label="Laxative administered",
                points=round(pts, 1), category="toileting", modifiable=False,
                evidence=[Evidence("MedicationAdministration", most_recent.drug_name, timestamp=most_recent.administered_at)],
            ))

    # --- Procedures & devices ---
    if state.admit_datetime:
        postop_events = [e for e in state.events if e.type == "surgery"]
        for pe in postop_events:
            days_postop = (now - pe.timestamp).days
            if 0 <= days_postop <= 2:
                factors.append(Factor(
                    id="postop_day_0_2", label=f"Post-op day {days_postop}",
                    points=cfg.get("fls", "procedures", "postop_day_0_2", default=5),
                    category="procedures", modifiable=False,
                    evidence=[Evidence("Procedure", "surgery", timestamp=pe.timestamp)],
                ))
                break

    if "nerve_block_lower_limb" in state.devices:
        factors.append(Factor(
            id="nerve_block", label="Active lower-limb nerve block",
            points=cfg.get("fls", "procedures", "nerve_block", default=10),
            category="procedures", modifiable=True,
        ))

    if "epidural" in state.devices:
        factors.append(Factor(
            id="epidural", label="Epidural infusion",
            points=cfg.get("fls", "procedures", "epidural", default=6),
            category="procedures", modifiable=True,
        ))

    tether_types = {"iv_pole", "foley", "o2_tubing", "telemetry", "scd", "drain"}
    active_tethers = tether_types.intersection(state.devices)
    if len(active_tethers) >= cfg.get("fls", "procedures", "tethers_threshold", default=2):
        factors.append(Factor(
            id="tethers", label=f"≥ 2 tethers ({len(active_tethers)} active)",
            points=cfg.get("fls", "procedures", "tethers_points", default=4),
            category="procedures", modifiable=True,
            evidence=[Evidence("DeviceUseStatement", ", ".join(sorted(active_tethers)))],
        ))

    # --- Sensory & communication ---
    sensory_dx = {"H54", "H90", "H91", "H93"}
    if any(d[:3] in sensory_dx for d in state.diagnoses):
        factors.append(Factor(
            id="vision_hearing", label="Vision or hearing impairment",
            points=cfg.get("fls", "sensory", "vision_hearing", default=3),
            category="sensory", modifiable=False,
        ))

    if any(e.type == "interpreter_needed" for e in state.events):
        factors.append(Factor(
            id="interpreter", label="Interpreter needed",
            points=cfg.get("fls", "sensory", "interpreter", default=3),
            category="sensory", modifiable=False,
        ))

    # --- Sleep ---
    start_h = cfg.get("fls", "sleep", "overnight_start_hour", default=23)
    end_h = cfg.get("fls", "sleep", "overnight_end_hour", default=5)
    threshold = cfg.get("fls", "sleep", "overnight_interruptions_threshold", default=2)

    def _is_overnight(ts: datetime) -> bool:
        return ts.hour >= start_h or ts.hour < end_h

    overnight_interruptions = [
        e for e in state.events
        if e.type in ("vitals_check", "lab_draw") and _is_overnight(e.timestamp)
        and e.timestamp >= now - timedelta(hours=24)
    ]
    if len(overnight_interruptions) >= threshold:
        factors.append(Factor(
            id="sleep_interruptions", label=f"≥ {threshold} overnight interruptions",
            points=cfg.get("fls", "sleep", "overnight_interruptions_points", default=3),
            category="sleep", modifiable=True,
            evidence=[Evidence("Event", f"{len(overnight_interruptions)} interruptions 23:00–05:00")],
        ))

    return factors
