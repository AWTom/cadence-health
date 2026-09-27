"""PT shift plan — streams an 8-hour physical therapy schedule from Bedrock."""
from __future__ import annotations
import os
from typing import Iterator

import boto3

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "openai.gpt-oss-120b-1:0")
TOP_N = 8

SYSTEM_PROMPT = """You are a senior physical therapist at a skilled nursing facility.
Write a schedule for ONE physical therapist's 8-hour shift (07:00-15:30, with a 30-minute lunch)
covering the residents provided, highest Care Level first. Leave short gaps for documentation.

Use exactly this plain-text format for every visit, with no markdown tables or asterisks:

HH:MM-HH:MM · Room <room> · <name> (Level <care level>)
Focus: <one line on the main fall/injury risk to address>
- <treatment step>
- <treatment step>
- <treatment step>

Put lunch and documentation blocks on their own line as "HH:MM-HH:MM · Lunch" or
"HH:MM-HH:MM · Documentation". End with one line starting "Handoff:" (no time prefix) for the nursing team.
Keep treatment steps short, concrete and safe for frail older adults."""

_client = None


def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    return _client


def _describe(p: dict) -> str:
    factors = ", ".join(f["label"] for f in p["factors"][:4]) or "none recorded"
    return (
        f"- Room {p['bed']} · {p['name']} · Care Level {p['care_level']} ({p['care_level_name']}) · "
        f"EHI {p['ehi']:.0f} (fall score {p['fall_score']:.0f} {p['fall_level']}, "
        f"injury {p['injury_level']}: bone {p['bone_level']}, bleed {p['bleed_level']}) · "
        f"{p['description']} · top factors: {factors}"
    )


def stream_pt_plan(patients: list[dict]) -> Iterator[str]:
    # Care Level first; EHI orders residents within a level (spec 1.3)
    top = sorted(patients, key=lambda p: (p["care_level"], p["ehi"]), reverse=True)[:TOP_N]
    prompt = "Residents to see today:\n" + "\n".join(_describe(p) for p in top)

    try:
        response = _bedrock().converse_stream(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 4000, "temperature": 0.3},
            additionalModelRequestFields={"reasoning_effort": "low"},
        )
        for event in response["stream"]:
            # gpt-oss also streams reasoningContent deltas; only forward the answer text.
            text = event.get("contentBlockDelta", {}).get("delta", {}).get("text")
            if text:
                yield text
    except Exception as e:  # surface failures in the modal instead of a silent cut-off
        yield f"\n\n[PT plan generation failed: {e}]"
