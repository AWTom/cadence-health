import { useState, useMemo } from "react";
import type { BedConfig, PatientScore } from "../../types";
import { CARE_LEVEL_NAMES } from "../../types";
import { BedTile } from "./BedTile";

interface Props {
  beds: BedConfig[];
  patients: PatientScore[];
  onSelectPatient: (p: PatientScore | null) => void;
  selectedPatientId: string | null;
}

// Nursing home (small-house model) layout — beds are placed by hall + slot
const ROOM_W = 110;
const ROOM_H = 85;
const PITCH = 118;       // horizontal spacing between rooms
const NORTH_Y = 30;      // top of north rooms
const SOUTH_Y = 505;     // top of south rooms
const LEFT_X = 70;       // x of first room

// Derived zones
const NORTH_BOTTOM = NORTH_Y + ROOM_H;           // 115
const SOUTH_TOP = SOUTH_Y;                        // 505
const CORRIDOR_N_Y = NORTH_BOTTOM;               // 115 — top of north corridor
const CORRIDOR_N_H = 45;                          // north corridor band height
const CORRIDOR_S_Y = SOUTH_TOP - 45;             // 460 — top of south corridor
const SUPPORT_TOP = CORRIDOR_N_Y + CORRIDOR_N_H; // 160 — top of central support zone
const SUPPORT_BOT = CORRIDOR_S_Y;                 // 460 — bottom of central support zone
const SUPPORT_H = SUPPORT_BOT - SUPPORT_TOP;      // 300

const bedPos = (bed: BedConfig) => ({
  x: LEFT_X + bed.slot * PITCH,
  y: bed.hall === "maple" ? NORTH_Y : SOUTH_Y,
});

const NUM_ROOMS = 10;
const UNIT_RIGHT = LEFT_X + (NUM_ROOMS - 1) * PITCH + ROOM_W; // rightmost edge of rooms
const SVG_W = UNIT_RIGHT + 70;
const SVG_H = SOUTH_Y + ROOM_H + 60;

// Central support zone x-ranges
const ELEV_X = 20;
const ELEV_W = LEFT_X - ELEV_X;                  // 50 — elevator lobby width
const UTIL_X = LEFT_X;
const UTIL_W = 110;
const NS_X = UTIL_X + UTIL_W + 8;
const NS_W = 580;
const STAIR_X = UNIT_RIGHT;
const STAIR_W = 50;

export function FloorMap({ beds, patients, onSelectPatient, selectedPatientId }: Props) {
  const [tierFilter, setTierFilter] = useState<number>(0);

  const patientByBed = useMemo(() => {
    const map = new Map<string, PatientScore>();
    for (const p of patients) map.set(p.bed, p);
    return map;
  }, [patients]);

  const filteredBedIds = useMemo(() => {
    if (!tierFilter) return new Set(beds.map((b) => b.bed_id));
    return new Set(
      beds
        .filter((b) => {
          const p = patientByBed.get(b.bed_id);
          return p ? p.care_level === tierFilter : false;
        })
        .map((b) => b.bed_id)
    );
  }, [beds, patientByBed, tierFilter]);

  return (
    <div className="flex flex-col gap-3">
      {/* Tier filter strip */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Filter</span>
        <button
          onClick={() => setTierFilter(0)}
          className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${tierFilter === 0 ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-500 border-slate-200 hover:border-slate-400 hover:text-slate-700"}`}
        >
          All
        </button>
        {[1, 2, 3, 4, 5].map((t) => {
          const cnt = patients.filter((p) => p.care_level === t).length;
          const active = tierFilter === t;
          const accents = ["#3b82f6","#06b6d4","#f59e0b","#f97316","#ef4444"][t-1];
          return (
            <button
              key={t}
              onClick={() => setTierFilter(active ? 0 : t)}
              className="px-3 py-1 rounded-full text-xs font-semibold border transition-all"
              style={active
                ? { background: accents, color: "#fff", borderColor: accents }
                : { background: "#fff", color: accents, borderColor: accents + "55" }}
            >
              L{t} · {cnt}
            </button>
          );
        })}
      </div>

      {/* SVG floor plan */}
      <div className="overflow-auto border border-slate-200 rounded-xl bg-white shadow-sm">
        <svg
          width={SVG_W}
          height={SVG_H}
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          style={{ minWidth: SVG_W }}
        >
          {/* ── Building outline ── */}
          <rect
            x={ELEV_X} y={NORTH_Y}
            width={STAIR_X + STAIR_W + 20 - ELEV_X}
            height={SOUTH_Y + ROOM_H - NORTH_Y}
            rx={4} fill="none" stroke="#94a3b8" strokeWidth={2}
          />

          {/* ── Wing labels ── */}
          <text x={SVG_W / 2} y={16} textAnchor="middle" fontSize={10} fill="#0ea5e9" fontWeight="600">
            ↑ Courtyard Garden
          </text>

          {/* ── Corridor bands ── */}
          <rect x={ELEV_X} y={CORRIDOR_N_Y} width={STAIR_X + STAIR_W + 20 - ELEV_X} height={CORRIDOR_N_H}
            fill="#f0f9ff" stroke="none" />
          <text x={ELEV_X + 4} y={CORRIDOR_N_Y + 28} fontSize={9} fill="#0ea5e9">Maple Hall · Resident Rooms 101–110</text>
          <rect x={ELEV_X} y={CORRIDOR_S_Y} width={STAIR_X + STAIR_W + 20 - ELEV_X} height={45}
            fill="#f0fdf4" stroke="none" />
          <text x={ELEV_X + 4} y={CORRIDOR_S_Y + 28} fontSize={9} fill="#16a34a">Oak Hall · Resident Rooms 111–120</text>

          {/* ── Shared core background ── */}
          <rect x={ELEV_X} y={SUPPORT_TOP} width={STAIR_X + STAIR_W + 20 - ELEV_X} height={SUPPORT_H}
            fill="#f8fafc" stroke="none" />

          {/* ── Main entrance / lobby ── */}
          <rect x={ELEV_X} y={SUPPORT_TOP} width={ELEV_W} height={SUPPORT_H}
            fill="#e2e8f0" stroke="#94a3b8" strokeWidth={1} />
          <text x={ELEV_X + ELEV_W / 2} y={SUPPORT_TOP + SUPPORT_H / 2}
            textAnchor="middle" fontSize={9} fill="#475569" fontWeight="600"
            transform={`rotate(-90,${ELEV_X + ELEV_W / 2},${SUPPORT_TOP + SUPPORT_H / 2})`}>
            MAIN ENTRANCE
          </text>

          {/* ── Left core: spa/tub room + laundry ── */}
          {[
            { y: SUPPORT_TOP, label: ["Spa /", "Tub Room"], fill: "#e0f2fe", stroke: "#0284c7", text: "#075985" },
            { y: SUPPORT_TOP + SUPPORT_H / 2 + 2, label: ["Laundry /", "Soiled Utility"], fill: "#fce7f3", stroke: "#db2777", text: "#9d174d" },
          ].map((r) => (
            <g key={r.label[0]}>
              <rect x={UTIL_X} y={r.y} width={UTIL_W} height={SUPPORT_H / 2 - 2}
                fill={r.fill} stroke={r.stroke} strokeWidth={1} strokeDasharray="3,2" />
              <text x={UTIL_X + UTIL_W / 2} y={r.y + SUPPORT_H / 4 - 4} textAnchor="middle" fontSize={8} fill={r.text}>{r.label[0]}</text>
              <text x={UTIL_X + UTIL_W / 2} y={r.y + SUPPORT_H / 4 + 7} textAnchor="middle" fontSize={8} fill={r.text}>{r.label[1]}</text>
            </g>
          ))}

          {/* ── Central commons: dining · nurse station · living room ── */}
          <rect x={NS_X} y={SUPPORT_TOP + 12} width={NS_W / 3 - 6} height={SUPPORT_H - 24}
            rx={8} fill="#fefce8" stroke="#fde68a" strokeWidth={1.5} />
          <text x={NS_X + NS_W / 6} y={SUPPORT_TOP + SUPPORT_H / 2 - 4} textAnchor="middle" fontSize={11} fill="#92400e" fontWeight="700">Dining Room</text>
          <text x={NS_X + NS_W / 6} y={SUPPORT_TOP + SUPPORT_H / 2 + 10} textAnchor="middle" fontSize={8} fill="#b45309">+ Open Kitchen</text>

          <rect x={NS_X + NS_W / 3} y={SUPPORT_TOP + 60} width={NS_W / 3} height={SUPPORT_H - 120}
            rx={8} fill="#eff6ff" stroke="#bfdbfe" strokeWidth={1.5} />
          <text x={NS_X + NS_W / 2} y={SUPPORT_TOP + SUPPORT_H / 2 - 4} textAnchor="middle" fontSize={12} fill="#1e40af" fontWeight="700">Nurse Station</text>
          <text x={NS_X + NS_W / 2} y={SUPPORT_TOP + SUPPORT_H / 2 + 12} textAnchor="middle" fontSize={8} fill="#3b82f6">Sunrise Care Center · 1st Floor</text>

          <rect x={NS_X + (NS_W * 2) / 3 + 6} y={SUPPORT_TOP + 12} width={NS_W / 3 - 6} height={SUPPORT_H - 24}
            rx={8} fill="#f0fdf4" stroke="#bbf7d0" strokeWidth={1.5} />
          <text x={NS_X + (NS_W * 5) / 6} y={SUPPORT_TOP + SUPPORT_H / 2 - 4} textAnchor="middle" fontSize={11} fill="#166534" fontWeight="700">Living Room</text>
          <text x={NS_X + (NS_W * 5) / 6} y={SUPPORT_TOP + SUPPORT_H / 2 + 10} textAnchor="middle" fontSize={8} fill="#15803d">Activities · Hearth</text>

          {/* ── Right core: med room + therapy ── */}
          {[
            { y: SUPPORT_TOP, label: ["Med Room /", "Clean Utility"], fill: "#fef9c3", stroke: "#d97706", text: "#92400e" },
            { y: SUPPORT_TOP + SUPPORT_H / 2 + 2, label: ["Rehab /", "Therapy"], fill: "#ede9fe", stroke: "#7c3aed", text: "#5b21b6" },
          ].map((r) => (
            <g key={r.label[0]}>
              <rect x={NS_X + NS_W + 8} y={r.y} width={UTIL_W} height={SUPPORT_H / 2 - 2}
                fill={r.fill} stroke={r.stroke} strokeWidth={1} strokeDasharray="3,2" />
              <text x={NS_X + NS_W + 8 + UTIL_W / 2} y={r.y + SUPPORT_H / 4 - 4} textAnchor="middle" fontSize={8} fill={r.text}>{r.label[0]}</text>
              <text x={NS_X + NS_W + 8 + UTIL_W / 2} y={r.y + SUPPORT_H / 4 + 7} textAnchor="middle" fontSize={8} fill={r.text}>{r.label[1]}</text>
            </g>
          ))}

          {/* ── Exit to garden ── */}
          <rect x={STAIR_X} y={SUPPORT_TOP} width={STAIR_W} height={SUPPORT_H}
            fill="#e2e8f0" stroke="#94a3b8" strokeWidth={1} />
          <text x={STAIR_X + STAIR_W / 2} y={SUPPORT_TOP + SUPPORT_H / 2}
            textAnchor="middle" fontSize={8} fill="#475569" fontWeight="600"
            transform={`rotate(-90,${STAIR_X + STAIR_W / 2},${SUPPORT_TOP + SUPPORT_H / 2})`}>
            GARDEN EXIT
          </text>

          {/* ── Horizontal dividers between rooms and corridors ── */}
          <line x1={ELEV_X} y1={NORTH_BOTTOM} x2={STAIR_X + STAIR_W + 20} y2={NORTH_BOTTOM}
            stroke="#94a3b8" strokeWidth={1.5} />
          <line x1={ELEV_X} y1={SOUTH_TOP} x2={STAIR_X + STAIR_W + 20} y2={SOUTH_TOP}
            stroke="#94a3b8" strokeWidth={1.5} />

          {/* ── Vertical room separators (north wall) ── */}
          {Array.from({ length: NUM_ROOMS + 1 }, (_, i) => (
            <line key={`ns${i}`}
              x1={LEFT_X + i * PITCH} y1={NORTH_Y}
              x2={LEFT_X + i * PITCH} y2={NORTH_BOTTOM}
              stroke="#cbd5e1" strokeWidth={1} />
          ))}
          {/* ── Vertical room separators (south wall) ── */}
          {Array.from({ length: NUM_ROOMS + 1 }, (_, i) => (
            <line key={`ss${i}`}
              x1={LEFT_X + i * PITCH} y1={SOUTH_TOP}
              x2={LEFT_X + i * PITCH} y2={SOUTH_TOP + ROOM_H}
              stroke="#cbd5e1" strokeWidth={1} />
          ))}

          {/* ── Camera coverage arcs ── */}
          {beds
            .filter((b) => b.has_camera)
            .map((b) => (
              <circle
                key={`cam-${b.bed_id}`}
                cx={bedPos(b).x + ROOM_W / 2}
                cy={bedPos(b).y + ROOM_H / 2}
                r={70}
                fill="none"
                stroke="#0ea5e9"
                strokeWidth={0.8}
                strokeDasharray="4,4"
                opacity={0.35}
              />
            ))}

          {/* ── South direction label ── */}
          <text x={SVG_W / 2} y={SVG_H - 6} textAnchor="middle" fontSize={10} fill="#16a34a" fontWeight="600">
            ↓ Parking / Visitor Entry
          </text>

          {/* ── Bed tiles ── */}
          {beds.map((bed) => (
            <BedTile
              key={bed.bed_id}
              bed={bed}
              {...bedPos(bed)}
              patient={filteredBedIds.has(bed.bed_id) ? patientByBed.get(bed.bed_id) : undefined}
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
                L{t}
              </span>
              {CARE_LEVEL_NAMES[t]}
            </span>
          );
        })}
        <span className="flex items-center gap-1 text-sky-500">
          <span className="inline-block w-4 h-0 border-t border-dashed border-sky-400" /> Camera radius
        </span>
        <span className="text-gray-400">⚠ Rising = score up ≥15 pts in 6h</span>
      </div>
    </div>
  );
}
