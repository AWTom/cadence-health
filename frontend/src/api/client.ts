import type { UnitDetail, PatientScore } from "../types";

const BASE = "/api";

export class HttpError extends Error {
  constructor(public status: number, statusText: string) {
    super(`${status} ${statusText}`);
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new HttpError(res.status, res.statusText);
  return res.json() as Promise<T>;
}

async function streamPost(path: string, body: unknown, onChunk: (text: string) => void, signal: AbortSignal) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    signal,
    ...(body === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  });
  if (!res.ok || !res.body) throw new HttpError(res.status, res.statusText);
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    onChunk(value);
  }
}

export const api = {
  getUnit: (unitId: string) => get<UnitDetail>(`/units/${unitId}`),
  getPatient: (patientId: string) => get<PatientScore>(`/patients/${patientId}`),
  getConfig: () => get<Record<string, unknown>>("/config"),

  /** Streams the PT shift plan as plain text, calling onChunk as tokens arrive. */
  streamPtPlan: (onChunk: (text: string) => void, signal: AbortSignal) =>
    streamPost("/pt-plan", undefined, onChunk, signal),

  /** Streams the cost savings report for a finished PT plan. */
  streamSavingsReport: (plan: string, onChunk: (text: string) => void, signal: AbortSignal) =>
    streamPost("/savings-report", { plan }, onChunk, signal),
};
