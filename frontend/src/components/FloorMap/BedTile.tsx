import { type PatientScore, type BedConfig } from "../../types";

interface Props {
  bed: BedConfig;
  x: number;
  y: number;
  patient: PatientScore | undefined;
  selected: boolean;
  onClick: () => void;
}

const W = 110;
const H = 88;

// Light-theme tier palette
const LIGHT_TIER: Record<number, { bg: string; accent: string; text: string; sub: string }> = {
  1: { bg: "#ffffff", accent: "#3b82f6", text: "#1e40af", sub: "#93c5fd" },
  2: { bg: "#ffffff", accent: "#06b6d4", text: "#0e7490", sub: "#67e8f9" },
  3: { bg: "#fffbeb", accent: "#f59e0b", text: "#92400e", sub: "#fcd34d" },
  4: { bg: "#fff7ed", accent: "#f97316", text: "#9a3412", sub: "#fdba74" },
  5: { bg: "#fff1f2", accent: "#ef4444", text: "#991b1b", sub: "#fca5a5" },
};

export function BedTile({ bed, x, y, patient, selected, onClick }: Props) {
  const tier = patient?.care_level ?? 0;
  const col = tier ? LIGHT_TIER[tier] : { bg: "#f8fafc", accent: "#cbd5e1", text: "#94a3b8", sub: "#e2e8f0" };

  const stroke = selected ? "#3b82f6" : col.accent + "99";
  const strokeW = selected ? 2.5 : 1.2;

  return (
    <g onClick={onClick} style={{ cursor: patient ? "pointer" : "default" }}
      aria-label={patient ? `Bed ${bed.bed_id}, Care Level ${tier}` : `Bed ${bed.bed_id} empty`}>

      {/* Drop shadow */}
      <rect x={x + 1} y={y + 2} width={W} height={H} rx={7} fill="rgba(0,0,0,0.06)" />

      {/* Card */}
      <rect x={x} y={y} width={W} height={H} rx={7}
        fill={col.bg} stroke={stroke} strokeWidth={strokeW} />

      {/* Top accent stripe */}
      {tier > 0 && (
        <rect x={x + 1} y={y + 1} width={W - 2} height={5} rx={6}
          fill={col.accent} />
      )}

      {/* Room number */}
      <text x={x + 7} y={y + 20}
        fontSize={9.5} fill={col.text} fontWeight="700" fontFamily="monospace">
        {bed.bed_id}
      </text>

      {/* Tier pill */}
      {tier > 0 && (
        <>
          <rect x={x + W - 30} y={y + 9} width={24} height={14} rx={7}
            fill={col.accent} fillOpacity={0.18} />
          <text x={x + W - 18} y={y + 20}
            fontSize={9} fill={col.text} textAnchor="middle" fontWeight="800">
            L{tier}
          </text>
        </>
      )}

      {patient ? (
        <>
          {/* EHI value */}
          <text x={x + 7} y={y + 44}
            fontSize={22} fill={col.text} fontWeight="800" opacity={0.9}>
            {Math.round(patient.ehi)}
          </text>
          <text x={x + 7 + (patient.ehi >= 100 ? 38 : patient.ehi >= 10 ? 28 : 18)} y={y + 43}
            fontSize={8} fill={col.text} opacity={0.45} fontWeight="600">EHI</text>

          {/* Fall Score bar */}
          <rect x={x + 7} y={y + 52} width={W - 14} height={4} rx={2} fill={col.sub} fillOpacity={0.4} />
          <rect x={x + 7} y={y + 52}
            width={Math.max(0, Math.min(patient.fall_score / 100, 1) * (W - 14))} height={4} rx={2}
            fill={tier >= 4 ? "#f97316" : tier === 3 ? "#f59e0b" : "#3b82f6"} />

          {/* Injury bar — bone percentile within the facility */}
          <rect x={x + 7} y={y + 60} width={W - 14} height={4} rx={2} fill={col.sub} fillOpacity={0.4} />
          <rect x={x + 7} y={y + 60}
            width={Math.max(0, Math.min(patient.bone_percentile / 100, 1) * (W - 14))} height={4} rx={2}
            fill="#a78bfa" />

          {/* Bar labels */}
          <text x={x + 7} y={y + H - 6} fontSize={7} fill={col.text} opacity={0.4}>FALL</text>
          <text x={x + 32} y={y + H - 6} fontSize={7} fill={col.text} opacity={0.4}>BONE</text>

          {/* Rising flag */}
          {patient.risk_rising && (
            <text x={x + W - 7} y={y + H - 6}
              fontSize={9} textAnchor="end" fill="#f97316" fontWeight="700">↑</text>
          )}
          {/* Camera dot */}
          {bed.has_camera && !patient.risk_rising && (
            <circle cx={x + W - 10} cy={y + H - 10} r={3}
              fill="#0ea5e9" opacity={0.5} />
          )}
        </>
      ) : (
        <text x={x + W / 2} y={y + H / 2 + 8}
          textAnchor="middle" fontSize={9} fill="#cbd5e1" fontWeight="500">vacant</text>
      )}
    </g>
  );
}
