"""FallGuard API — FastAPI application."""
from __future__ import annotations
import asyncio
import json
import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from scoring.models import ScoringConfig
from scoring.nursing_home import score_unit
from synthetic.generator import build_demo_unit
from api.pt_plan import stream_pt_plan
from api.savings_report import stream_savings_report

CONFIG_PATH = Path(__file__).parents[1] / "scoring_config.yaml"

app = FastAPI(title="FallGuard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_cfg: ScoringConfig | None = None
_demo_unit: dict | None = None
_connected_clients: list[WebSocket] = []


def get_config() -> ScoringConfig:
    global _cfg
    if _cfg is None:
        raw = yaml.safe_load(CONFIG_PATH.read_text())
        _cfg = ScoringConfig(version=raw["version"], raw=raw)
    return _cfg


def get_demo_unit() -> dict:
    global _demo_unit
    if _demo_unit is None:
        _demo_unit = build_demo_unit(datetime.utcnow())
    return _demo_unit


def _score_to_dict(result, patient_meta: dict, cfg: ScoringConfig) -> dict:
    care = cfg.get("nursing_home", "care_levels", result.care_level, default={})
    return {
        "patient_id": result.patient_id,
        "name": patient_meta.get("name", result.patient_id),
        "bed": patient_meta.get("bed", ""),
        "description": patient_meta.get("description", ""),
        "calculated_at": result.calculated_at.isoformat(),
        "fall_score": result.fall_score,
        "fall_level": result.fall_level,
        "bone_points": result.bone_points,
        "bone_percentile": result.bone_percentile,
        "bone_level": result.bone_level,
        "bleed_level": result.bleed_level,
        "injury_level": result.injury_level,
        "ehi": result.ehi,
        "care_level": result.care_level,
        "care_level_name": care.get("name", ""),
        "care_actions": care.get("actions", ""),
        "config_version": result.config_version,
        "data_gaps": result.data_gaps,
        "risk_rising": result.risk_rising,
        "phenotype": result.phenotype,
        "factors": [
            {
                "id": f.id,
                "label": f.label,
                "points": f.points,
                "category": f.category,
                "modifiable": f.modifiable,
                "evidence": [
                    {
                        "source": e.source,
                        "value": str(e.value),
                        "unit": e.unit,
                        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    }
                    for e in f.evidence
                ],
            }
            for f in sorted(result.factors, key=lambda x: x.points, reverse=True)
        ],
    }


def _scored_patients(now: datetime) -> list[dict]:
    """Score the whole facility at once — bone levels are banded by facility percentile."""
    cfg = get_config()
    patients = get_demo_unit()["patients"]
    results = score_unit([p["state"] for p in patients], now, cfg)
    return [_score_to_dict(r, p, cfg) for r, p in zip(results, patients)]


@app.get("/health")
def health():
    return {"status": "ok", "synthetic": True}


@app.get("/api/units")
def list_units():
    unit = get_demo_unit()
    return [{
        "unit_id": unit["unit_id"],
        "name": unit["name"],
        "bed_count": len(unit["beds"]),
        "patient_count": len(unit["patients"]),
    }]


@app.get("/api/units/{unit_id}")
def get_unit(unit_id: str):
    unit = get_demo_unit()
    scored_patients = _scored_patients(datetime.utcnow())

    return {
        "unit_id": unit["unit_id"],
        "name": unit["name"],
        "beds": unit["beds"],
        "patients": scored_patients,
        "summary": {
            "total": len(scored_patients),
            "by_care_level": {
                str(level): sum(1 for p in scored_patients if p["care_level"] == level)
                for level in range(1, 6)
            },
        },
    }


@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: str):
    patient = next((p for p in _scored_patients(datetime.utcnow()) if p["patient_id"] == patient_id), None)
    if not patient:
        from fastapi import HTTPException
        raise HTTPException(404, detail="Patient not found")
    return patient


@app.post("/api/pt-plan")
def pt_plan():
    """Stream an 8-hour PT shift plan for the highest-risk residents (plain text)."""
    return StreamingResponse(
        stream_pt_plan(_scored_patients(datetime.utcnow())),
        media_type="text/plain; charset=utf-8",
    )


class SavingsReportRequest(BaseModel):
    plan: str


@app.post("/api/savings-report")
def savings_report(req: SavingsReportRequest):
    """Stream an administrative cost savings report for a PT plan (plain text, tool-driven math)."""
    return StreamingResponse(
        stream_savings_report(req.plan, _scored_patients(datetime.utcnow()), get_config().raw),
        media_type="text/plain; charset=utf-8",
    )


@app.get("/api/config")
def get_scoring_config():
    cfg = get_config()
    return cfg.raw


@app.websocket("/ws/unit/{unit_id}")
async def unit_websocket(websocket: WebSocket, unit_id: str):
    await websocket.accept()
    _connected_clients.append(websocket)
    try:
        while True:
            # Push updated scores every 15 seconds
            now = datetime.utcnow()
            scores = _scored_patients(now)

            await websocket.send_json({"type": "scores_update", "data": scores, "timestamp": now.isoformat()})
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        _connected_clients.remove(websocket)
