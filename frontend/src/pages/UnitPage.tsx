import { useEffect, useState } from "react";
import { api } from "../api/client";
import { FloorMap } from "../components/FloorMap/FloorMap";
import { PatientDrawer } from "../components/PatientDrawer/PatientDrawer";
import { PtPlanModal } from "../components/PtPlanModal/PtPlanModal";
import { useUnitWebSocket } from "../hooks/useWebSocket";
import type { UnitDetail, PatientScore } from "../types";
import { CARE_LEVEL_NAMES, byPriority } from "../types";

const UNIT_ID = "sunrise";

export function UnitPage() {
  const [unit, setUnit] = useState<UnitDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<PatientScore | null>(null);
  const [showPtPlan, setShowPtPlan] = useState(false);

  const { patients: wsPatients } = useUnitWebSocket(UNIT_ID);

  useEffect(() => {
    api.getUnit(UNIT_ID)
      .then(setUnit)
      .catch((e: Error) => setError(e.message));
  }, []);

  // Merge REST-loaded unit data with live WebSocket score updates
  const patients = wsPatients.length > 0 ? wsPatients : unit?.patients ?? [];

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-600 font-semibold">API Error: {error}</p>
          <p className="text-sm text-gray-500 mt-1">Make sure the backend is running: <code>uvicorn api.main:app --reload</code></p>
        </div>
      </div>
    );
  }

  if (!unit) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 text-sm">Loading unit data…</div>
      </div>
    );
  }

  const tierCounts = [1, 2, 3, 4, 5].map((t) => ({
    tier: t,
    count: patients.filter((p) => p.care_level === t).length,
  }));

  return (
    <div className="flex h-[calc(100vh-56px)] overflow-hidden">
      {/* Main content */}
      <div className="flex-1 overflow-y-auto p-4 min-w-0">
        {/* Unit header */}
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{unit.name}</h1>
            <p className="text-sm text-gray-500">{patients.length} patients · {unit.beds.length} beds</p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowPtPlan(true)}
              className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-semibold shadow-sm hover:bg-blue-700 transition-colors"
            >
              Generate PT plan
            </button>
          </div>
        </div>

        {/* Tier summary chips */}
        <div className="flex gap-2 mb-4 flex-wrap">
          {tierCounts.map(({ tier, count }) => {
            const accents = ["#3b82f6","#06b6d4","#f59e0b","#f97316","#ef4444"][tier-1];
            return (
              <div key={tier} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border shadow-sm"
                style={{ borderColor: accents + "44" }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: accents }} />
                <span className="text-xs font-semibold" style={{ color: accents }}>L{tier}</span>
                <span className="text-xs text-slate-400">{CARE_LEVEL_NAMES[tier]}</span>
                <span className="text-sm font-bold text-slate-800 ml-0.5">{count}</span>
              </div>
            );
          })}
        </div>

        {/* Floor map */}
        <FloorMap
          beds={unit.beds}
          patients={patients}
          onSelectPatient={setSelectedPatient}
          selectedPatientId={selectedPatient?.patient_id ?? null}
        />

        {/* List view — sorted by EHI */}
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">All Residents — by Care Level, then Harm Index</h2>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-400 uppercase tracking-wide border-b border-slate-200">
                <tr>
                  <th className="px-3 py-2 text-left">Bed</th>
                  <th className="px-3 py-2 text-left">Patient</th>
                  <th className="px-3 py-2 text-center">Care Level</th>
                  <th className="px-3 py-2 text-right">Fall</th>
                  <th className="px-3 py-2 text-left">Injury</th>
                  <th className="px-3 py-2 text-right">EHI</th>
                  <th className="px-3 py-2 text-left">Flags</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[...patients]
                  .sort(byPriority)
                  .map((p) => {
                    const accent = ["#3b82f6","#06b6d4","#f59e0b","#f97316","#ef4444"][p.care_level-1];
                    return (
                    <tr
                      key={p.patient_id}
                      onClick={() => setSelectedPatient(selectedPatient?.patient_id === p.patient_id ? null : p)}
                      className={`cursor-pointer transition-colors ${selectedPatient?.patient_id === p.patient_id ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <td className="px-3 py-2 font-mono text-slate-500 text-xs">{p.bed}</td>
                      <td className="px-3 py-2 text-slate-700 font-medium">{p.name}</td>
                      <td className="px-3 py-2 text-center">
                        <span className="px-2 py-0.5 rounded-full text-xs font-bold"
                          style={{ background: accent + "18", color: accent }}>L{p.care_level}</span>
                      </td>
                      <td className="px-3 py-2 text-right text-slate-600">{p.fall_score}</td>
                      <td className="px-3 py-2 text-slate-600">{p.injury_level}</td>
                      <td className="px-3 py-2 text-right font-bold text-slate-800">{p.ehi.toFixed(0)}</td>
                      <td className="px-3 py-2 text-xs text-orange-500 font-medium">
                        {p.risk_rising && "↑ Rising "}
                        {p.data_gaps.length > 0 && "⚠ Gap"}
                      </td>
                    </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showPtPlan && <PtPlanModal onClose={() => setShowPtPlan(false)} />}

      {/* Patient drawer — slides in from right */}
      {selectedPatient && (
        <div className="w-96 border-l border-slate-200 bg-white shadow-xl flex-shrink-0 overflow-hidden">
          <PatientDrawer patient={selectedPatient} onClose={() => setSelectedPatient(null)} />
        </div>
      )}
    </div>
  );
}
