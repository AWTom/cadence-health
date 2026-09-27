import { byPriority, type PatientScore } from "../../types";

const VISITS = 6;
const VISIT_MIN = 45;
const DOC_MIN = 10;

const fmt = (min: number) =>
  `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;

function steps(p: PatientScore): string[] {
  const ids = new Set(p.factors.map((f) => f.id));
  const out: string[] = [];
  if (ids.has("mobility")) out.push("Supervised sit-to-stand and pivot transfers with gait belt");
  if (ids.has("cognition")) out.push("Short, repeated cues; practice calling for help before standing");
  if (ids.has("bathroom_urgency")) out.push("Rehearse safe night-time route to the bathroom");
  if (ids.has("fall_risk_meds") || ids.has("recent_change")) out.push("Check orthostatic vitals before and after walking");
  if (p.bleed_level !== "Low") out.push("Prioritize fall-safe technique; report any head strike immediately");
  out.push("Seated lower-limb strengthening (heel raises, marching)", "Confirm walker, glasses and call light are in reach");
  return out.slice(0, 3);
}

/** Deterministic sample plan used when the live PT plan endpoint is unavailable. */
export function buildMockPlan(patients: PatientScore[]): string {
  const top = [...patients].sort(byPriority).slice(0, VISITS);
  const lines: string[] = [];
  let t = 7 * 60;
  top.forEach((p, i) => {
    if (i === 3) {
      lines.push(`${fmt(t)}-${fmt(t + 30)} · Lunch`, "");
      t += 30;
    }
    const focus = p.factors.find((f) => f.category !== "bone" && f.category !== "bleed");
    lines.push(
      `${fmt(t)}-${fmt(t + VISIT_MIN)} · Room ${p.bed} · ${p.name} (Level ${p.care_level})`,
      `Focus: ${focus ? focus.label : "General mobility and fall prevention"}`,
      ...steps(p).map((s) => `- ${s}`),
      "",
      `${fmt(t + VISIT_MIN)}-${fmt(t + VISIT_MIN + DOC_MIN)} · Documentation`,
      "",
    );
    t += VISIT_MIN + DOC_MIN;
  });
  lines.push("Handoff: Keep gait belts and walkers in reach for all residents seen today; flag any new dizziness to nursing.");
  return lines.join("\n");
}

/** Replays text word by word so the fallback feels like the live stream. */
export async function streamText(text: string, onChunk: (t: string) => void, signal: AbortSignal) {
  for (const word of text.split(/(?<=\s)/)) {
    if (signal.aborted) return;
    onChunk(word);
    await new Promise((r) => setTimeout(r, 12));
  }
}
