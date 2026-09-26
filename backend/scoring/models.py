from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Tier(int, Enum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


@dataclass
class Evidence:
    source: str        # e.g. "MedicationAdministration", "Observation/vitals"
    value: Any         # raw value
    unit: str = ""
    timestamp: datetime | None = None
    code: str = ""     # FHIR/LOINC/RxNorm code


@dataclass
class Factor:
    id: str
    label: str
    points: float
    category: str      # history | age | cognition | medications | hemodynamics | mobility | toileting | procedures | sensory | sleep | bone | bleed
    modifiable: bool
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class PatientState:
    patient_id: str
    encounter_id: str
    age: int
    sex: Sex
    events: list[ClinicalEvent] = field(default_factory=list)

    # Pre-grouped convenience accessors (populated by the DB layer before passing to engine)
    diagnoses: list[str] = field(default_factory=list)       # ICD-10 codes
    active_medications: list[MedOrder] = field(default_factory=list)
    med_administrations: list[MedAdmin] = field(default_factory=list)
    vitals: list[Observation] = field(default_factory=list)
    labs: list[Observation] = field(default_factory=list)
    assessments: list[Observation] = field(default_factory=list)
    procedures: list[str] = field(default_factory=list)      # SNOMED codes
    devices: list[str] = field(default_factory=list)         # active device types

    # Derived / cached fields
    weight_kg: float | None = None
    height_cm: float | None = None
    bmi: float | None = None
    weight_30d_ago_kg: float | None = None
    admit_datetime: datetime | None = None


@dataclass
class ClinicalEvent:
    type: str
    code: str
    value: Any
    unit: str
    timestamp: datetime
    source: str


@dataclass
class MedOrder:
    drug_name: str
    rxnorm: str
    frid_classes: list[str] = field(default_factory=list)
    is_anticoagulant: bool = False
    is_antiplatelet: bool = False
    is_bone_weakening: bool = False
    is_osteoporosis_therapy: bool = False
    anticholinergic_burden: int = 0
    ordered_at: datetime | None = None
    dose_changed_at: datetime | None = None


@dataclass
class MedAdmin:
    drug_name: str
    rxnorm: str
    frid_classes: list[str] = field(default_factory=list)
    is_diuretic: bool = False
    is_laxative: bool = False
    is_prn_sedative_opioid: bool = False
    administered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Observation:
    loinc: str
    value: float | str
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    category: str = ""  # vitals | laboratory | survey


@dataclass
class ScoreResult:
    patient_id: str
    encounter_id: str
    calculated_at: datetime
    fls: float
    iss_bone: float
    iss_bleed: float
    iss: float
    ehi: float
    tier: Tier
    factors: list[Factor]
    config_version: str
    data_gaps: list[str] = field(default_factory=list)
    risk_rising: bool = False


@dataclass
class ScoringConfig:
    version: str
    raw: dict  # full parsed YAML — engine reads values from this

    def get(self, *path: str, default: Any = None) -> Any:
        node = self.raw
        for key in path:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
            if node is None:
                return default
        return node
