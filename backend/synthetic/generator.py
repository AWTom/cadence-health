"""Synthetic nursing home residents for the FallGuard demo (MDS-shaped records)."""
from __future__ import annotations
import random
from datetime import datetime, timedelta

from scoring.nursing_home import Med, ResidentState


def _days(now: datetime, n: float) -> datetime:
    return now - timedelta(days=n)


# Scripted residents — each illustrates a scoring pattern from the spec.

def _mrs_a(now: datetime) -> ResidentState:
    """Spec worked example: impulsive transferrer on apixaban with a recent fall → Care Level 5."""
    return ResidentState(
        patient_id="P001", age=86, female=True, mds_assessed_at=_days(now, 40),
        fall_dates=[_days(now, 21)],
        fall_mobility="needs_help_gets_up_alone", walking="independent", transfers="independent",
        adl="independent", cognition="moderate", bladder="continent", bmi=20.0,
        meds=[
            Med("sertraline", {"ssri", "antidepressant"}),
            Med("lorazepam", {"benzodiazepine"}, started_at=_days(now, 4)),
            Med("apixaban", {"anticoagulant"}),
        ],
        fall_score_7d_ago=60,
    )


def _mr_b(now: datetime) -> ResidentState:
    """Spec worked example: bedbound, total dependence — looks frail, low fracture risk → Care Level 1."""
    return ResidentState(
        patient_id="P002", age=78, female=False, mds_assessed_at=_days(now, 20),
        fall_mobility="cannot_stand", walking="total", transfers="total", adl="total",
        bladder="total", bmi=27.0, pressure_ulcer=True,
        meds=[Med("quetiapine", {"antipsychotic"})],
    )


def _mobile_wanderer(now: datetime) -> ResidentState:
    return ResidentState(
        patient_id="P003", age=81, female=True, mds_assessed_at=_days(now, 60),
        fall_dates=[_days(now, 75)],
        fall_mobility="steady", walking="independent", transfers="independent", adl="extensive_1",
        cognition="severe", wanders=True, easily_distracted=True, bladder="frequent", bmi=19.2,
        meds=[Med("donepezil", {"cholinesterase_inhibitor"})],
    )


def _night_toileter(now: datetime) -> ResidentState:
    return ResidentState(
        patient_id="P004", age=79, female=False, mds_assessed_at=_days(now, 30),
        fall_dates=[_days(now, 45)],
        fall_mobility="aid_or_supervision", walking="limited", transfers="limited", adl="extensive_1",
        cognition="intact", bladder="frequent", urgency=True, diabetes=True, bmi=24.5,
        meds=[
            Med("furosemide", {"diuretic"}, last_given_at=now.replace(hour=8, minute=0)),
            Med("metoprolol", {"antihypertensive"}),
            Med("warfarin", {"anticoagulant"}),
        ],
    )


def _acute_change(now: datetime) -> ResidentState:
    return ResidentState(
        patient_id="P005", age=74, female=True, mds_assessed_at=_days(now, 110),  # overdue → data gap
        fall_mobility="aid_or_supervision", walking="limited", transfers="extensive", adl="extensive_2",
        cognition="moderate", bladder="frequent", dizziness_orthostatic_or_vision=True, bmi=23.1,
        meds=[
            Med("oxycodone", {"opioid"}, started_at=_days(now, 3)),
            Med("nitrofurantoin", {"antibiotic"}, started_at=_days(now, 2)),
        ],
        acute_changes=[("Hospital return", _days(now, 3)), ("UTI, antibiotic started", _days(now, 2))],
        fall_score_7d_ago=25,
    )


SCRIPTED = [
    (_mrs_a, "114", "86F, walker, gets up alone, fell 3 wks ago, new lorazepam, apixaban"),
    (_mr_b, "105", "78M, bedbound, total dependence, quetiapine"),
    (_mobile_wanderer, "102", "81F, severe dementia, walks independently, wanders, BMI 19"),
    (_night_toileter, "116", "79M, walker, morning furosemide, urgency, warfarin"),
    (_acute_change, "119", "74F, back from hospital, UTI on antibiotics, new oxycodone"),
]

_FALL_RISK_MEDS = [
    Med("lisinopril", {"antihypertensive"}), Med("trazodone", {"antidepressant", "sleep"}),
    Med("gabapentin", {"anticonvulsant"}), Med("tramadol", {"opioid"}),
    Med("citalopram", {"ssri", "antidepressant"}), Med("tamsulosin", {"alpha_blocker"}),
]


def _filler(pid: str, now: datetime, seed: int) -> ResidentState:
    rng = random.Random(seed)
    mobility = rng.choice(["steady", "aid_or_supervision", "aid_or_supervision", "cannot_stand"])
    dependent = mobility == "cannot_stand"
    return ResidentState(
        patient_id=pid, age=rng.randint(68, 96), female=rng.random() < 0.65,
        mds_assessed_at=_days(now, rng.randint(5, 85)),
        fall_dates=[_days(now, rng.randint(40, 170))] if rng.random() < 0.3 else [],
        fall_mobility=mobility,
        walking="total" if dependent else rng.choice(["independent", "limited", "extensive"]),
        transfers="total" if dependent else rng.choice(["independent", "limited", "extensive"]),
        adl="total" if dependent else rng.choice(["independent", "extensive_1", "extensive_2", "dependent"]),
        cognition=rng.choice(["intact", "intact", "moderate", "severe"]),
        bladder=rng.choice(["continent", "frequent", "total"]),
        diabetes=rng.random() < 0.25, osteoarthritis=rng.random() < 0.3,
        bmi=round(rng.uniform(18, 33), 1),
        meds=rng.sample(_FALL_RISK_MEDS, k=rng.randint(0, 2)),
    )


# Sunrise Care Center — small-house nursing home, two resident halls around a shared core.
# Each bed is placed by hall + slot (0-9, west→east); the frontend owns pixel layout.

def _build_beds() -> list[dict]:
    beds = []
    for hall, first_room, low_bed_slots in (("maple", 101, (0, 5, 9)), ("oak", 111, (1, 6, 9))):
        for slot in range(10):
            room = str(first_room + slot)
            beds.append({
                "bed_id": room,
                "room": room,
                "hall": hall,
                "slot": slot,
                "distance_to_station": round(abs(slot - 4.5) + 1, 1),  # slots 4/5 nearest nurse station
                "has_camera": slot in (3, 4, 5, 6),
                "low_bed": slot in low_bed_slots,
                "has_alarm": True,
            })
    return beds


UNIT_BEDS = _build_beds()


def build_demo_unit(now: datetime) -> dict:
    """Build the demo facility: five scripted residents + filler residents."""
    patients = []
    for make, bed, desc in SCRIPTED:
        state = make(now)
        patients.append({"id": state.patient_id, "name": f"Resident {state.patient_id[1:]}",
                         "bed": bed, "state": state, "description": desc})
    used = {p["bed"] for p in patients}
    for i, bed in enumerate([b for b in UNIT_BEDS if b["bed_id"] not in used][:12]):
        pid = f"P{10 + i:03d}"
        patients.append({"id": pid, "name": f"Resident {pid[1:]}", "bed": bed["bed_id"],
                         "state": _filler(pid, now, i), "description": "Long-stay resident"})

    return {
        "unit_id": "sunrise",
        "name": "Sunrise Care Center · Maple & Oak Halls",
        "beds": UNIT_BEDS,
        "patients": patients,
    }
