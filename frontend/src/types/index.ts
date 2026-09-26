export interface Evidence {
  source: string;
  value: string;
  unit: string;
  timestamp: string | null;
}

export interface Factor {
  id: string;
  label: string;
  points: number;
  category: string;
  modifiable: boolean;
  evidence: Evidence[];
}

export interface PatientScore {
  patient_id: string;
  name: string;
  bed: string;
  description: string;
  calculated_at: string;
  fls: number;
  iss_bone: number;
  iss_bleed: number;
  iss: number;
  ehi: number;
  tier: 1 | 2 | 3 | 4 | 5;
  config_version: string;
  data_gaps: string[];
  risk_rising: boolean;
  factors: Factor[];
}

export interface BedConfig {
  bed_id: string;
  room: string;
  distance_to_station: number;
  has_camera: boolean;
  low_bed: boolean;
  has_alarm: boolean;
  x: number;
  y: number;
}

export interface UnitDetail {
  unit_id: string;
  name: string;
  beds: BedConfig[];
  patients: PatientScore[];
  summary: {
    total: number;
    by_tier: Record<string, number>;
  };
}

export const TIER_LABELS: Record<number, string> = {
  1: "Low",
  2: "Low-Mod",
  3: "Moderate",
  4: "High",
  5: "Critical",
};

export const TIER_COLORS: Record<number, { bg: string; text: string; border: string }> = {
  1: { bg: "#dbeafe", text: "#1e40af", border: "#93c5fd" },
  2: { bg: "#e0f2fe", text: "#0369a1", border: "#7dd3fc" },
  3: { bg: "#fef9c3", text: "#854d0e", border: "#fde047" },
  4: { bg: "#fed7aa", text: "#9a3412", border: "#fb923c" },
  5: { bg: "#ff6b2b", text: "#ffffff", border: "#c2410c" },
};
