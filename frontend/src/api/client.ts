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
};
