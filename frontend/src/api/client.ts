import type { UnitDetail, PatientScore } from "../types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  getUnit: (unitId: string) => get<UnitDetail>(`/units/${unitId}`),
  getPatient: (patientId: string) => get<PatientScore>(`/patients/${patientId}`),
  getConfig: () => get<Record<string, unknown>>("/config"),

  /** Streams the PT shift plan as plain text, calling onChunk as tokens arrive. */
  streamPtPlan: async (onChunk: (text: string) => void, signal: AbortSignal) => {
    const res = await fetch(`${BASE}/pt-plan`, { method: "POST", signal });
    if (!res.ok || !res.body) throw new Error(`${res.status} ${res.statusText}`);
    const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) return;
      onChunk(value);
    }
  },
};
