"""Administrative cost savings report — Bedrock tool-use loop over a PT plan.

The model never does arithmetic: every dollar figure comes from calculate_savings,
which reads its assumptions from scoring_config.yaml (roi + interventions).
"""
from __future__ import annotations
import math
import re
from typing import Iterator

from api.pt_plan import BEDROCK_MODEL_ID, _bedrock

MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """You are a healthcare finance analyst for a skilled nursing facility.
Given today's physical therapy (PT) shift plan, estimate the annual dollar impact of the
fall-prevention interventions in it for the facility administrator.

Always use the tools: look up the residents in the plan, read the cost assumptions, then call
calculate_savings. Include "pt_exercise" in fall_interventions for every resident seen by PT; add
other interventions only if the plan clearly implies them. Never compute or invent numbers yourself;
report only figures returned by the tools, formatted as whole dollars.

Write plain text (no markdown, no tables, no asterisks) in exactly this shape:

Administrative Cost Savings Report
Summary: <one or two sentences with the total estimated annual savings>

By resident:
- Room <room> · <name> (Level <care level>): $<savings>/yr · <falls avoided> falls avoided
(one line per resident)

Totals: $<total savings>/yr · <total falls avoided> falls avoided · <injurious falls avoided> injurious falls avoided

Assumptions: <one or two sentences naming the key assumptions and their sources>
Caveat: Estimates use heuristic assumptions from scoring_config.yaml and must be calibrated on facility data."""

TOOLS = {"tools": [
    {"toolSpec": {
        "name": "get_residents",
        "description": "Look up risk details for residents by room number: name, Care Level, Fall Score, fall/injury/bleed levels.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {"rooms": {"type": "array", "items": {"type": "string"}}},
            "required": ["rooms"],
        }},
    }},
    {"toolSpec": {
        "name": "get_cost_assumptions",
        "description": "Return the facility's cost-per-fall figures, fall probability model and intervention effectiveness rates.",
        "inputSchema": {"json": {"type": "object", "properties": {}}},
    }},
    {"toolSpec": {
        "name": "calculate_savings",
        "description": "Deterministically estimate annual falls avoided and dollars saved for the given residents and interventions.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {
                "rooms": {"type": "array", "items": {"type": "string"}},
                "fall_interventions": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["pt_exercise", "sitter", "virtual_monitor", "bed_alarm"]},
                },
                "injury_interventions": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["low_bed", "hip_protector"]},
                },
            },
            "required": ["rooms", "fall_interventions"],
        }},
    }},
]}


# ── Tools (pure, deterministic) ───────────────────────────────────────────────

def _by_room(patients: list[dict], rooms: list[str]) -> list[dict]:
    wanted = {str(r).strip() for r in rooms}
    return [p for p in patients if p["bed"] in wanted]


def get_residents(patients: list[dict], rooms: list[str]) -> dict:
    return {"residents": [
        {k: p[k] for k in ("bed", "name", "care_level", "care_level_name", "fall_score",
                           "fall_level", "injury_level", "bleed_level")}
        for p in _by_room(patients, rooms)
    ]}


def get_cost_assumptions(cfg: dict) -> dict:
    return {"roi": cfg.get("roi", {}), "interventions": cfg.get("interventions", {})}


def calculate_savings(patients: list[dict], cfg: dict, rooms: list[str],
                      fall_interventions: list[str], injury_interventions: list[str] | None = None) -> dict:
    roi, iv = cfg.get("roi", {}), cfg.get("interventions", {})
    c_inj = roi.get("cost_per_injurious_fall", 14000)
    c_non = roi.get("cost_per_non_injurious_fall", 1000)
    fall_red = 1 - math.prod(1 - iv.get(f"{k}_fall_reduction", 0) for k in fall_interventions)
    inj_red = 1 - math.prod(1 - iv.get(f"{k}_injury_reduction", 0) for k in injury_interventions or [])

    rows = []
    for p in _by_room(patients, rooms):
        p_fall = min(roi.get("annual_fall_prob_cap", 0.9),
                     roi.get("annual_fall_prob_base", 0.1) + roi.get("annual_fall_prob_per_point", 0.008) * p["fall_score"])
        inj = roi.get("injurious_fall_fraction", {}).get(p["injury_level"], 0.1)
        p_after, inj_after = p_fall * (1 - fall_red), inj * (1 - inj_red)
        cost = lambda pf, fi: pf * (fi * c_inj + (1 - fi) * c_non)  # noqa: E731
        rows.append({
            "room": p["bed"], "name": p["name"], "care_level": p["care_level"],
            "baseline_falls_per_year": round(p_fall, 3),
            "falls_avoided_per_year": round(p_fall - p_after, 3),
            "injurious_falls_avoided_per_year": round(p_fall * inj - p_after * inj_after, 3),
            "savings_usd_per_year": round(cost(p_fall, inj) - cost(p_after, inj_after)),
        })
    return {
        "residents": rows,
        "fall_reduction_applied": round(fall_red, 3),
        "injury_reduction_applied": round(inj_red, 3),
        "totals": {
            "savings_usd_per_year": sum(r["savings_usd_per_year"] for r in rows),
            "falls_avoided_per_year": round(sum(r["falls_avoided_per_year"] for r in rows), 2),
            "injurious_falls_avoided_per_year": round(sum(r["injurious_falls_avoided_per_year"] for r in rows), 2),
        },
    }


def _run_tool(name: str, args: dict, patients: list[dict], cfg: dict) -> dict:
    if name == "get_residents":
        return get_residents(patients, args.get("rooms", []))
    if name == "get_cost_assumptions":
        return get_cost_assumptions(cfg)
    if name == "calculate_savings":
        return calculate_savings(patients, cfg, args.get("rooms", []), args.get("fall_interventions", []),
                                 args.get("injury_interventions"))
    return {"error": f"unknown tool {name}"}


TOOL_STATUS = {
    "get_residents": "Looking up residents in the plan",
    "get_cost_assumptions": "Reading cost assumptions",
    "calculate_savings": "Calculating savings",
}


# ── Loop ──────────────────────────────────────────────────────────────────────

def stream_savings_report(plan: str, patients: list[dict], cfg: dict) -> Iterator[str]:
    """Yields progress lines ("› …") while tools run, then the report text."""
    rooms = sorted(set(re.findall(r"Room (\d+)", plan)))
    messages = [{"role": "user", "content": [{"text": f"Rooms in plan: {', '.join(rooms)}\n\nPT plan:\n{plan}"}]}]
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = _bedrock().converse(
                modelId=BEDROCK_MODEL_ID,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages,
                toolConfig=TOOLS,
                inferenceConfig={"maxTokens": 3000, "temperature": 0.2},
                additionalModelRequestFields={"reasoning_effort": "low"},
            )
            message = response["output"]["message"]
            messages.append(message)
            tool_uses = [b["toolUse"] for b in message["content"] if "toolUse" in b]
            if not tool_uses:
                text = "".join(b.get("text", "") for b in message["content"])
                for line in text.splitlines(keepends=True):
                    yield line
                return
            results = []
            for tu in tool_uses:
                yield f"› {TOOL_STATUS.get(tu['name'], tu['name'])}…\n"
                output = _run_tool(tu["name"], tu.get("input") or {}, patients, cfg)
                results.append({"toolResult": {"toolUseId": tu["toolUseId"], "content": [{"json": output}]}})
            messages.append({"role": "user", "content": results})
        yield "\n[Report stopped: too many tool rounds]"
    except Exception as e:  # surface failures in the modal instead of a silent cut-off
        yield f"\n\n[Savings report failed: {e}]"

