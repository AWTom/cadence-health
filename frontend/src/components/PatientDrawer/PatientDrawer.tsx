import { TIER_COLORS, TIER_LABELS, type PatientScore, type Factor } from "../../types";

interface Props {
  patient: PatientScore;
  onClose: () => void;
}

const CATEGORY_ORDER = ["history", "cognition", "medications", "hemodynamics", "mobility", "toileting", "procedures", "sensory", "sleep", "bone", "bleed", "age"];

function ScoreBar({ value, max = 100, color }: { value: number; max?: number; color: string }) {
  return (
    <div className="relative h-3 rounded-full bg-gray-100 overflow-hidden w-full">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${(value / max) * 100}%`, background: color }}
      />
    </div>
  );
}

function FactorRow({ factor }: { factor: Factor }) {
  const newest = factor.evidence.reduce(
    (a, e) => (!a || (e.timestamp && e.timestamp > (a.timestamp ?? ""))) ? e : a,
    factor.evidence[0]
  );
  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
      <span className="min-w-[2.5rem] text-right font-bold text-gray-700">+{factor.points}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-gray-800">{factor.label}</span>
          {factor.modifiable && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
              Modifiable
            </span>
          )}
        </div>
        {newest && (
          <p className="text-xs text-gray-400 mt-0.5">
            {newest.source} · {newest.value}{newest.unit ? ` ${newest.unit}` : ""}
            {newest.timestamp ? ` · ${new Date(newest.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : ""}
          </p>
        )}
      </div>
      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 capitalize whitespace-nowrap">
        {factor.category}
      </span>
    </div>
  );
}

export function PatientDrawer({ patient, onClose }: Props) {
  const colors = TIER_COLORS[patient.tier];
  const topFactors = [...patient.factors]
    .sort((a, b) => b.points - a.points)
    .slice(0, 8);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span
              className="px-3 py-1 rounded-full text-sm font-bold"
              style={{ background: colors.bg, color: colors.text, border: `1.5px solid ${colors.border}` }}
            >
              T{patient.tier} — {TIER_LABELS[patient.tier]}
            </span>
            {patient.risk_rising && (
              <span className="px-2 py-0.5 rounded bg-orange-100 text-orange-700 text-xs font-semibold border border-orange-300">
                ⚠ Risk Rising
              </span>
            )}
          </div>
          <h2 className="text-lg font-semibold text-gray-900">{patient.name}</h2>
          <p className="text-sm text-gray-500">Bed {patient.bed} · {patient.description}</p>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-700 text-xl p-1 rounded"
          aria-label="Close drawer"
        >
          ✕
        </button>
      </div>

      {/* Score summary */}
      <div className="grid grid-cols-3 gap-3 p-4 border-b border-gray-200 bg-gray-50">
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Fall Likelihood</p>
          <p className="text-2xl font-bold text-gray-900">{patient.fls}</p>
          <ScoreBar value={patient.fls} color="#3b82f6" />
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Injury Severity</p>
          <p className="text-2xl font-bold text-gray-900">{patient.iss}</p>
          <div className="space-y-1">
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400 w-8">Bone</span>
              <ScoreBar value={patient.iss_bone} color="#8b5cf6" />
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400 w-8">Bleed</span>
              <ScoreBar value={patient.iss_bleed} color="#ef4444" />
            </div>
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Harm Index</p>
          <p className="text-2xl font-bold text-gray-900">{patient.ehi.toFixed(0)}</p>
          <ScoreBar value={patient.ehi} color={colors.border} />
          <p className="text-xs text-gray-400 mt-1">FLS × ISS / 100</p>
        </div>
      </div>

      {/* Data gaps */}
      {patient.data_gaps.length > 0 && (
        <div className="mx-4 mt-3 p-2 rounded bg-amber-50 border border-amber-200 text-xs text-amber-800">
          ⚠ Data gaps: {patient.data_gaps.join(", ")}
        </div>
      )}

      {/* Top contributing factors */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Top Contributing Factors
        </h3>
        <div>
          {topFactors.map((f) => (
            <FactorRow key={f.id} factor={f} />
          ))}
        </div>

        {patient.factors.length > 8 && (
          <p className="text-xs text-gray-400 mt-2 text-center">
            + {patient.factors.length - 8} more factors
          </p>
        )}
      </div>

      {/* Footer: last calculated */}
      <div className="p-3 border-t border-gray-200 text-xs text-gray-400">
        Scored {new Date(patient.calculated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} ·
        Config v{patient.config_version}
      </div>
    </div>
  );
}
