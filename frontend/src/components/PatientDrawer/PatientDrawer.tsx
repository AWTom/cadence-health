import { CARE_LEVEL_COLORS, type PatientScore, type Factor, type Level } from "../../types";

interface Props {
  patient: PatientScore;
  onClose: () => void;
}


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

const LEVEL_STYLE: Record<Level, string> = {
  Low: "bg-slate-100 text-slate-600",
  Medium: "bg-amber-100 text-amber-800",
  High: "bg-red-100 text-red-700",
};

function LevelPill({ level }: { level: Level }) {
  return <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${LEVEL_STYLE[level]}`}>{level}</span>;
}

function FactorRow({ factor }: { factor: Factor }) {
  const newest = factor.evidence.reduce(
    (a, e) => (!a || (e.timestamp && e.timestamp > (a.timestamp ?? ""))) ? e : a,
    factor.evidence[0]
  );
  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
      <span className="min-w-[2.5rem] text-right font-bold text-gray-700">
        {factor.points > 0 ? `+${factor.points}` : factor.points < 0 ? factor.points : "•"}
      </span>
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
  const colors = CARE_LEVEL_COLORS[patient.care_level];
  // Spec 1.5: explanations show the top 5 factors by points
  const fallFactors = patient.factors.filter((f) => f.category !== "bone" && f.category !== "bleed").slice(0, 5);
  const injuryFactors = patient.factors.filter((f) => f.category === "bone" || f.category === "bleed");

  return (
    <div className="flex flex-col h-full overflow-hidden bg-white">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-slate-100"
        style={{ background: `linear-gradient(to bottom right, ${colors.bg}, #ffffff)` }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span
              className="px-3 py-1 rounded-full text-sm font-bold"
              style={{ background: colors.bg, color: colors.text, border: `1.5px solid ${colors.border}` }}
            >
              Level {patient.care_level} — {patient.care_level_name}
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

      {/* Care actions */}
      <div className="px-4 py-3 border-b border-slate-100 text-sm text-slate-700">
        <span className="font-semibold">Actions: </span>{patient.care_actions}
      </div>

      {/* Score summary */}
      <div className="grid grid-cols-3 gap-3 p-4 border-b border-slate-100 bg-slate-50">
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Fall Score</p>
          <p className="text-2xl font-bold text-gray-900">{patient.fall_score}</p>
          <ScoreBar value={patient.fall_score} color="#3b82f6" />
          <div className="mt-1"><LevelPill level={patient.fall_level} /></div>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Injury</p>
          <div className="mb-1"><LevelPill level={patient.injury_level} /></div>
          <div className="space-y-1 text-xs text-gray-500">
            <div className="flex items-center justify-between gap-1">
              <span>Bone {patient.bone_points} pts · {patient.bone_percentile.toFixed(0)}th pct</span>
              <LevelPill level={patient.bone_level} />
            </div>
            <div className="flex items-center justify-between gap-1">
              <span>Bleed</span>
              <LevelPill level={patient.bleed_level} />
            </div>
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Harm Index</p>
          <p className="text-2xl font-bold text-gray-900">{patient.ehi.toFixed(0)}</p>
          <ScoreBar value={patient.ehi} color={colors.border} />
          <p className="text-xs text-gray-400 mt-1">Fall × bone percentile / 100</p>
        </div>
      </div>

      {/* Data gaps */}
      {patient.data_gaps.length > 0 && (
        <div className="mx-4 mt-3 p-2 rounded bg-amber-50 border border-amber-200 text-xs text-amber-800">
          ⚠ Data gaps: {patient.data_gaps.join(", ")}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Why they may fall</h3>
        {fallFactors.length ? fallFactors.map((f) => <FactorRow key={f.id} factor={f} />)
          : <p className="text-xs text-gray-400">No fall factors.</p>}

        <h3 className="text-sm font-semibold text-gray-700 mt-5 mb-2">Injury if they fall</h3>
        {injuryFactors.map((f) => <FactorRow key={f.id} factor={f} />)}
      </div>

      {/* Footer: last calculated */}
      <div className="p-3 border-t border-gray-200 text-xs text-gray-400">
        Scored {new Date(patient.calculated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} ·
        Config v{patient.config_version}
      </div>
    </div>
  );
}
