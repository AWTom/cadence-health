"""Synthetic patient data generator for FallGuard demo."""
from __future__ import annotations
import random
from datetime import datetime, timedelta
from typing import Any

from scoring.models import (
    PatientState, Sex, ClinicalEvent, MedOrder, MedAdmin, Observation
)


_RNG = random.Random(42)


def _dt(base: datetime, hours: float) -> datetime:
    return base + timedelta(hours=hours)


def _vitals_series(base: datetime, hours_back: int, sbp: int = 120, dbp: int = 75, hr: int = 78) -> list[Observation]:
    obs = []
    for h in range(hours_back, 0, -4):
        ts = base - timedelta(hours=h)
        obs += [
            Observation("8480-6", sbp + _RNG.randint(-8, 8), "mmHg", ts, "vitals"),
            Observation("8462-4", dbp + _RNG.randint(-5, 5), "mmHg", ts, "vitals"),
            Observation("8867-4", hr + _RNG.randint(-6, 6), "bpm", ts, "vitals"),
            Observation("59408-5", 97 + _RNG.randint(-2, 1), "%", ts, "vitals"),
        ]
    return obs


def make_tier5_patient(now: datetime) -> dict[str, Any]:
    """88-year-old woman, osteoporosis, prior hip fracture, apixaban, CAM-positive overnight."""
    admit = now - timedelta(days=3)
    state = PatientState(
        patient_id="P001",
        encounter_id="E001",
        age=88,
        sex=Sex.FEMALE,
        admit_datetime=admit,
        diagnoses=["M81.0", "Z87.39", "N18.3", "F03.90", "E11.9"],
        active_medications=[
            MedOrder("apixaban", "1364430", is_anticoagulant=True, frid_classes=[]),
            MedOrder("metoprolol", "866514", frid_classes=["antihypertensive"]),
            MedOrder("lorazepam", "141448", frid_classes=["benzodiazepine"], anticholinergic_burden=1,
                     dose_changed_at=now - timedelta(hours=3)),
        ],
        med_administrations=[
            MedAdmin("lorazepam", "141448", frid_classes=["benzodiazepine"],
                     is_prn_sedative_opioid=True, administered_at=now - timedelta(hours=2, minutes=50)),
        ],
        vitals=_vitals_series(now, 48, sbp=106, dbp=62),
        labs=[
            Observation("1751-7", 2.7, "g/dL", now - timedelta(hours=6), "laboratory"),
            Observation("718-7", 9.2, "g/dL", now - timedelta(hours=6), "laboratory"),
            Observation("62292-8", 14.0, "ng/mL", now - timedelta(days=30), "laboratory"),
        ],
        assessments=[
            Observation("55752-0", "positive", "", now - timedelta(hours=5), "survey"),  # CAM
            Observation("72461-0", 1, "", now - timedelta(hours=2), "survey"),           # RASS +1 (agitated)
            Observation("55755-3", "assist", "", now - timedelta(hours=8), "survey"),    # Mobility
        ],
        devices={"iv_pole", "foley", "telemetry"},
        events=[
            ClinicalEvent("fall_this_admission", "", "", "", now - timedelta(days=1), "FallEvent"),
            ClinicalEvent("overnight_interruption", "", "", "", now - timedelta(hours=3), "Event"),
            ClinicalEvent("overnight_interruption", "", "", "", now - timedelta(hours=1), "Event"),
        ],
        weight_kg=44.0,
        height_cm=158.0,
        bmi=17.6,
    )
    return {"id": "P001", "name": "Patient 001", "bed": "4E-14", "state": state,
            "description": "88F osteoporosis, prior hip fx, apixaban, CAM+, post-lorazepam"}


def make_postop_knee_patient(now: datetime) -> dict[str, Any]:
    """Post-op day 1 knee replacement, adductor canal block, PRN oxycodone."""
    admit = now - timedelta(days=1, hours=6)
    state = PatientState(
        patient_id="P002",
        encounter_id="E002",
        age=68,
        sex=Sex.MALE,
        admit_datetime=admit,
        diagnoses=["M17.11", "Z96.641"],
        active_medications=[
            MedOrder("oxycodone", "1049502", frid_classes=["opioid"]),
            MedOrder("celecoxib", "140587", frid_classes=[]),
            MedOrder("enoxaparin", "67253", is_anticoagulant=True),
        ],
        med_administrations=[
            MedAdmin("oxycodone", "1049502", frid_classes=["opioid"],
                     is_prn_sedative_opioid=True, administered_at=now - timedelta(hours=1, minutes=20)),
        ],
        vitals=_vitals_series(now, 24, sbp=124, dbp=78),
        labs=[
            Observation("718-7", 10.1, "g/dL", now - timedelta(hours=8), "laboratory"),
        ],
        assessments=[
            Observation("55755-3", "assist", "", now - timedelta(hours=4), "survey"),
        ],
        devices={"nerve_block_lower_limb", "iv_pole", "scd", "foley"},
        events=[
            ClinicalEvent("surgery", "TKR", "", "", now - timedelta(days=1, hours=4), "Procedure"),
            ClinicalEvent("joint_replacement", "TKR", "", "", now - timedelta(days=1, hours=4), "Procedure"),
        ],
        weight_kg=91.0,
        height_cm=178.0,
        bmi=28.7,
    )
    return {"id": "P002", "name": "Patient 002", "bed": "4E-08", "state": state,
            "description": "68M post-op day 1 TKR, adductor canal block, PRN oxycodone"}


def make_low_risk_patient(now: datetime) -> dict[str, Any]:
    """45-year-old with pneumonia, no fall risk factors."""
    admit = now - timedelta(days=2)
    state = PatientState(
        patient_id="P003",
        encounter_id="E003",
        age=45,
        sex=Sex.MALE,
        admit_datetime=admit,
        diagnoses=["J18.9"],
        active_medications=[
            MedOrder("azithromycin", "308460", frid_classes=[]),
            MedOrder("ceftriaxone", "309076", frid_classes=[]),
        ],
        med_administrations=[],
        vitals=_vitals_series(now, 48, sbp=118, dbp=74),
        labs=[
            Observation("718-7", 13.5, "g/dL", now - timedelta(hours=10), "laboratory"),
        ],
        assessments=[
            Observation("55755-3", "independent", "", now - timedelta(hours=6), "survey"),
        ],
        devices={"iv_pole"},
        events=[],
        weight_kg=82.0,
        height_cm=175.0,
        bmi=26.8,
    )
    return {"id": "P003", "name": "Patient 003", "bed": "4E-02", "state": state,
            "description": "45M pneumonia, no fall risk factors"}


def make_dialysis_warfarin_patient(now: datetime) -> dict[str, Any]:
    """Dialysis, low BMI, warfarin, INR 3.4."""
    admit = now - timedelta(days=5)
    state = PatientState(
        patient_id="P004",
        encounter_id="E004",
        age=72,
        sex=Sex.MALE,
        admit_datetime=admit,
        diagnoses=["N18.6", "Z99.2", "I48.91", "E11.9", "M81.0"],
        active_medications=[
            MedOrder("warfarin", "11289", is_anticoagulant=True, frid_classes=[]),
            MedOrder("furosemide", "202991", frid_classes=["diuretic"]),
            MedOrder("atorvastatin", "617311", frid_classes=[]),
        ],
        med_administrations=[
            MedAdmin("furosemide", "202991", frid_classes=["diuretic"],
                     is_diuretic=True, administered_at=now - timedelta(hours=3)),
        ],
        vitals=_vitals_series(now, 72, sbp=148, dbp=88),
        labs=[
            Observation("6301-6", 3.4, "", now - timedelta(hours=8), "laboratory"),   # INR
            Observation("1751-7", 2.8, "g/dL", now - timedelta(hours=8), "laboratory"),
            Observation("718-7", 8.8, "g/dL", now - timedelta(hours=8), "laboratory"),
            Observation("62292-8", 12.0, "ng/mL", now - timedelta(days=14), "laboratory"),
        ],
        assessments=[
            Observation("55755-3", "assist", "", now - timedelta(hours=10), "survey"),
        ],
        devices={"iv_pole", "telemetry"},
        events=[],
        weight_kg=54.0,
        height_cm=172.0,
        bmi=18.3,
    )
    return {"id": "P004", "name": "Patient 004", "bed": "4E-06", "state": state,
            "description": "72M dialysis, warfarin, INR 3.4, low BMI"}


def make_ciwa_patient(now: datetime) -> dict[str, Any]:
    """Alcohol withdrawal, rising CIWA score."""
    admit = now - timedelta(hours=18)
    state = PatientState(
        patient_id="P005",
        encounter_id="E005",
        age=54,
        sex=Sex.MALE,
        admit_datetime=admit,
        diagnoses=["F10.239", "K70.30"],
        active_medications=[
            MedOrder("chlordiazepoxide", "2598", frid_classes=["benzodiazepine"], anticholinergic_burden=1),
            MedOrder("thiamine", "9054", frid_classes=[]),
        ],
        med_administrations=[
            MedAdmin("chlordiazepoxide", "2598", frid_classes=["benzodiazepine"],
                     is_prn_sedative_opioid=True, administered_at=now - timedelta(hours=1)),
        ],
        vitals=_vitals_series(now, 18, sbp=158, dbp=94, hr=108),
        labs=[
            Observation("2339-0", 74.0, "mg/dL", now - timedelta(hours=4), "laboratory"),
        ],
        assessments=[
            Observation("74771-0", 14.0, "", now - timedelta(hours=2), "survey"),   # CIWA = 14
            Observation("72461-0", 2, "", now - timedelta(hours=2), "survey"),      # RASS +2
            Observation("55755-3", "assist", "", now - timedelta(hours=6), "survey"),
        ],
        devices={"iv_pole", "telemetry"},
        events=[
            ClinicalEvent("vitals_check", "", "", "", now - timedelta(hours=1), "Nursing"),
            ClinicalEvent("vitals_check", "", "", "", now - timedelta(minutes=30), "Nursing"),
            ClinicalEvent("lab_draw", "", "", "", now - timedelta(hours=4), "Lab"),
            ClinicalEvent("lab_draw", "", "", "", now - timedelta(minutes=20), "Lab"),
        ],
        weight_kg=79.0,
        height_cm=180.0,
        bmi=24.4,
    )
    return {"id": "P005", "name": "Patient 005", "bed": "4E-11", "state": state,
            "description": "54M alcohol withdrawal, CIWA 14, rising"}


# Canonical demo unit — 28 beds on 4-East Med/Surg
UNIT_BEDS = [
    {"bed_id": f"4E-{n:02d}", "room": f"4{n//2*2+1:02d}", "distance_to_station": max(1, abs(n - 7)),
     "has_camera": n in (1, 2, 7, 8), "low_bed": n % 4 == 0, "has_alarm": True,
     "x": (n % 7) * 140 + 60, "y": (n // 7) * 120 + 80}
    for n in range(1, 29)
]


def build_demo_unit(now: datetime) -> dict:
    """Build a full demo unit with all five scripted patients + filler patients."""
    scripted = [
        make_tier5_patient(now),
        make_postop_knee_patient(now),
        make_low_risk_patient(now),
        make_dialysis_warfarin_patient(now),
        make_ciwa_patient(now),
    ]

    # Fill remaining beds with low-to-moderate risk patients
    filler_beds = [b for b in UNIT_BEDS if b["bed_id"] not in {p["bed"] for p in scripted}]
    fillers = []
    for i, bed in enumerate(filler_beds[:10]):
        fillers.append({
            "id": f"P{10+i:03d}",
            "name": f"Patient {10+i:03d}",
            "bed": bed["bed_id"],
            "state": _make_filler_patient(f"P{10+i:03d}", now, i),
            "description": "General medical patient",
        })

    return {
        "unit_id": "4E",
        "name": "4-East Medical/Surgical",
        "beds": UNIT_BEDS,
        "patients": scripted + fillers,
    }


def _make_filler_patient(pid: str, now: datetime, seed: int) -> PatientState:
    rng = random.Random(seed)
    age = rng.randint(35, 90)
    return PatientState(
        patient_id=pid,
        encounter_id=f"E{pid}",
        age=age,
        sex=rng.choice([Sex.MALE, Sex.FEMALE]),
        admit_datetime=now - timedelta(days=rng.randint(1, 7)),
        diagnoses=rng.choices(["J18.9", "I50.9", "N18.3", "E11.9", "M54.5"], k=rng.randint(1, 3)),
        active_medications=[
            MedOrder("lisinopril", "29046", frid_classes=["antihypertensive"])
        ] if age > 60 else [],
        med_administrations=[],
        vitals=_vitals_series(now, 24),
        labs=[Observation("718-7", rng.uniform(10, 14), "g/dL", now - timedelta(hours=8), "laboratory")],
        assessments=[Observation("55755-3", "independent", "", now - timedelta(hours=8), "survey")],
        devices={"iv_pole"} if rng.random() > 0.3 else set(),
        events=[],
        weight_kg=rng.uniform(55, 100),
        height_cm=rng.uniform(155, 185),
        bmi=rng.uniform(20, 32),
    )
