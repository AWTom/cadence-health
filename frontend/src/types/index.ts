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

export type Level = "Low" | "Medium" | "High";

export interface PatientScore {
  patient_id: string;
  name: string;
  bed: string;
  description: string;
  calculated_at: string;
  fall_score: number;
  fall_level: Level;
  bone_points: number;
  bone_percentile: number;
  bone_level: Level;
  bleed_level: Level;
  injury_level: Level;
  ehi: number;
  care_level: 1 | 2 | 3 | 4 | 5;
  care_level_name: string;
  care_actions: string;
  config_version: string;
  data_gaps: string[];
  risk_rising: boolean;
  phenotype: string | null;
  factors: Factor[];
}

export interface BedConfig {
  bed_id: string;
  room: string;
  hall: "maple" | "oak";
  slot: number;
  distance_to_station: number;
  has_camera: boolean;
  low_bed: boolean;
  has_alarm: boolean;
}

export interface UnitDetail {
  unit_id: string;
  name: string;
  beds: BedConfig[];
  patients: PatientScore[];
  summary: {
    total: number;
    by_care_level: Record<string, number>;
  };
}

export const CARE_LEVEL_NAMES: Record<number, string> = {
  1: "Routine",
  2: "Watch",
  3: "Careful",
  4: "High Alert",
  5: "Top Priority",
};

/** Care Level first, then EHI within a level (spec 1.3). */
export const byPriority = (a: PatientScore, b: PatientScore) =>
  b.care_level - a.care_level || b.ehi - a.ehi;

export const CARE_LEVEL_COLORS: Record<number, { bg: string; text: string; border: string }> = {
  1: { bg: "#dbeafe", text: "#1e40af", border: "#93c5fd" },
  2: { bg: "#e0f2fe", text: "#0369a1", border: "#7dd3fc" },
  3: { bg: "#fef9c3", text: "#854d0e", border: "#fde047" },
  4: { bg: "#fed7aa", text: "#9a3412", border: "#fb923c" },
  5: { bg: "#ff6b2b", text: "#ffffff", border: "#c2410c" },
};
