import { useState, useMemo } from "react";
import type { BedConfig, PatientScore } from "../../types";
import { TIER_LABELS } from "../../types";
import { BedTile } from "./BedTile";

interface Props {
  beds: BedConfig[];
  patients: PatientScore[];
  onSelectPatient: (p: PatientScore | null) => void;
  selectedPatientId: string | null;
}

const TIER_FILTER_OPTIONS = [0, 1, 2, 3, 4, 5] as const;

export function FloorMap({ beds, patients, onSelectPatient, selectedPatientId }: Props) {
  const [tierFilter, setTierFilter] = useState<number>(0);

  const patientByBed = useMemo(() => {
    const map = new Map<string, PatientScore>();
    for (const p of patients) map.set(p.bed, p);
    return map;
  }, [patients]);

  const visibleBeds = useMemo(() => {
    if (!tierFilter) return beds;
    return beds.filter((b) => {
      const p = patientByBed.get(b.bed_id);
      return p ? p.tier === tierFilter : false;
    });
  }, [beds, patientByBed, tierFilter]);

  const xs = beds.map((b) => b.x);
  const ys = beds.map((b) => b.y);
  const svgW = Math.max(...xs) + 180;
  const svgH = Math.max(...ys) + 160;

  return (
    <div className="flex flex-col gap-3">
      {/* Tier filter strip */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-gray-500 font-medium">Filter:</span>
        <button
          onClick={() => setTierFilter(0)}
          className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${tierFilter === 0 ? "bg-gray-700 text-white border-gray-700" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}
        >
          All
        </button>
        {[1, 2, 3, 4, 5].map((t) => {
          const cnt = patients.filter((p) => p.tier === t).length;
          return (
            <button
              key={t}
              onClick={() => setTierFilter(tierFilter === t ? 0 : t)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${tierFilter === t ? "bg-gray-700 text-white border-gray-700" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}
            >
              T{t} {TIER_LABELS[t]} ({cnt})
            </button>
          );
        })}
      </div>

      {/* SVG floor plan */}
      <div className="overflow-auto border border-gray-200 rounded-xl bg-gray-50">
        <svg width={svgW} height={svgH} viewBox={`0 0 ${svgW} ${svgH}`}>
          {/* Nurses' station */}
          <rect x={10} y={10} width={140} height={50} rx={6} fill="#1e3a5f" />
          <text x={80} y={32} textAnchor="middle" fontSize={11} fill="white" fontWeight="600">
            Nurses' Station
          </text>
          <text x={80} y={48} textAnchor="middle" fontSize={9} fill="#94a3b8">
            Camera coverage: beds 1,2,7,8
          </text>

          {/* Bed tiles */}
          {beds.map((bed) => (
            <BedTile
              key={bed.bed_id}
              bed={bed}
              patient={
                visibleBeds.some((b) => b.bed_id === bed.bed_id)
                  ? patientByBed.get(bed.bed_id)
                  : undefined
              }
              selected={
                selectedPatientId !== null &&
                patientByBed.get(bed.bed_id)?.patient_id === selectedPatientId
              }
              onClick={() => {
                const p = patientByBed.get(bed.bed_id);
                if (p) onSelectPatient(selectedPatientId === p.patient_id ? null : p);
              }}
            />
          ))}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500 flex-wrap">
        {[1, 2, 3, 4, 5].map((t) => {
          const colors = [
            { bg: "#dbeafe", border: "#93c5fd", text: "#1e40af" },
            { bg: "#e0f2fe", border: "#7dd3fc", text: "#0369a1" },
            { bg: "#fef9c3", border: "#fde047", text: "#854d0e" },
            { bg: "#fed7aa", border: "#fb923c", text: "#9a3412" },
            { bg: "#ff6b2b", border: "#c2410c", text: "#ffffff" },
          ][t - 1];
          return (
            <span key={t} className="flex items-center gap-1">
              <span
                style={{ background: colors.bg, border: `1.5px solid ${colors.border}`, color: colors.text }}
                className="px-2 py-0.5 rounded font-semibold"
              >
                T{t}
              </span>
              {TIER_LABELS[t]}
            </span>
          );
        })}
        <span className="text-gray-400 ml-2">⚠ Rising = score rose ≥15 pts in 6h</span>
      </div>
    </div>
  );
}
