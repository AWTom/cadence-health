import { TIER_COLORS, TIER_LABELS, type PatientScore, type BedConfig } from "../../types";

interface Props {
  bed: BedConfig;
  patient: PatientScore | undefined;
  selected: boolean;
  onClick: () => void;
}

export function BedTile({ bed, patient, selected, onClick }: Props) {
  const tier = patient?.tier ?? 0;
  const colors = tier ? TIER_COLORS[tier] : { bg: "#f3f4f6", text: "#6b7280", border: "#d1d5db" };

  return (
    <g
      onClick={onClick}
      style={{ cursor: patient ? "pointer" : "default" }}
      aria-label={patient ? `Bed ${bed.bed_id}, Tier ${tier} ${TIER_LABELS[tier]}` : `Bed ${bed.bed_id} empty`}
    >
      <rect
        x={bed.x}
        y={bed.y}
        width={110}
        height={85}
        rx={6}
        fill={colors.bg}
        stroke={selected ? "#1d4ed8" : colors.border}
        strokeWidth={selected ? 3 : 1.5}
      />
      {/* Bed ID */}
      <text x={bed.x + 8} y={bed.y + 16} fontSize={10} fill={colors.text} fontWeight="600">
        {bed.bed_id}
      </text>
      {/* Tier badge */}
      {patient && (
        <>
          <rect
            x={bed.x + 68}
            y={bed.y + 5}
            width={34}
            height={18}
            rx={3}
            fill={colors.border}
          />
          <text x={bed.x + 85} y={bed.y + 18} fontSize={10} fill={colors.text} textAnchor="middle" fontWeight="700">
            T{tier}
          </text>

          {/* FLS / ISS mini-bars */}
          <text x={bed.x + 8} y={bed.y + 38} fontSize={9} fill="#6b7280">FLS</text>
          <rect x={bed.x + 28} y={bed.y + 28} width={74} height={8} rx={2} fill="#e5e7eb" />
          <rect x={bed.x + 28} y={bed.y + 28} width={Math.max(0, patient.fls * 0.74)} height={8} rx={2}
            fill={tier >= 4 ? "#f97316" : tier >= 3 ? "#eab308" : "#3b82f6"} />

          <text x={bed.x + 8} y={bed.y + 54} fontSize={9} fill="#6b7280">ISS</text>
          <rect x={bed.x + 28} y={bed.y + 44} width={74} height={8} rx={2} fill="#e5e7eb" />
          <rect x={bed.x + 28} y={bed.y + 44} width={Math.max(0, patient.iss * 0.74)} height={8} rx={2}
            fill="#8b5cf6" />

          {/* Status flags */}
          <text x={bed.x + 6} y={bed.y + 74} fontSize={8} fill={colors.text}>
            {patient.risk_rising ? "⚠ Rising" : ""}
            {patient.data_gaps.length > 0 ? " ⚠ Gap" : ""}
          </text>

          {/* Icons: camera, alarm */}
          {bed.has_camera && (
            <text x={bed.x + 90} y={bed.y + 74} fontSize={10} textAnchor="middle">📷</text>
          )}
        </>
      )}
      {!patient && (
        <text x={bed.x + 55} y={bed.y + 48} fontSize={10} fill="#9ca3af" textAnchor="middle">
          Empty
        </text>
      )}
    </g>
  );
}
