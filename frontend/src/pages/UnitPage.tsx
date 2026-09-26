import { useEffect, useState } from "react";
import { api } from "../api/client";
import { FloorMap } from "../components/FloorMap/FloorMap";
import { PatientDrawer } from "../components/PatientDrawer/PatientDrawer";
import { useUnitWebSocket } from "../hooks/useWebSocket";
import type { UnitDetail, PatientScore } from "../types";
import { TIER_LABELS } from "../types";

export function UnitPage() {
  const [unit, setUnit] = useState<UnitDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<PatientScore | null>(null);

  const { patients: wsPatients, connected } = useUnitWebSocket("4E");

  useEffect(() => {
    api.getUnit("4E")
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
    count: patients.filter((p) => p.tier === t).length,
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
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-gray-400"}`} />
            <span className="text-xs text-gray-500">{connected ? "Live" : "Polling"}</span>
          </div>
        </div>

        {/* Tier summary chips */}
        <div className="flex gap-2 mb-4 flex-wrap">
          {tierCounts.map(({ tier, count }) => (
            <div key={tier} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border bg-white shadow-sm">
              <span className="text-xs font-bold text-gray-600">T{tier}</span>
              <span className="text-xs text-gray-500">{TIER_LABELS[tier]}</span>
              <span className="ml-1 text-sm font-bold text-gray-900">{count}</span>
            </div>
          ))}
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
          <h2 className="text-sm font-semibold text-gray-700 mb-2">All Patients — sorted by Harm Index</h2>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="px-3 py-2 text-left">Bed</th>
                  <th className="px-3 py-2 text-left">Patient</th>
                  <th className="px-3 py-2 text-center">Tier</th>
                  <th className="px-3 py-2 text-right">FLS</th>
                  <th className="px-3 py-2 text-right">ISS</th>
                  <th className="px-3 py-2 text-right">EHI</th>
                  <th className="px-3 py-2 text-left">Flags</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[...patients]
                  .sort((a, b) => b.ehi - a.ehi)
                  .map((p) => (
                    <tr
                      key={p.patient_id}
                      onClick={() => setSelectedPatient(selectedPatient?.patient_id === p.patient_id ? null : p)}
                      className={`cursor-pointer hover:bg-blue-50 transition-colors ${selectedPatient?.patient_id === p.patient_id ? "bg-blue-50" : ""}`}
                    >
                      <td className="px-3 py-2 font-mono text-gray-600">{p.bed}</td>
                      <td className="px-3 py-2 text-gray-800">{p.name}</td>
                      <td className="px-3 py-2 text-center">
                        <span className="font-bold text-gray-700">T{p.tier}</span>
                      </td>
                      <td className="px-3 py-2 text-right font-medium">{p.fls}</td>
                      <td className="px-3 py-2 text-right font-medium">{p.iss}</td>
                      <td className="px-3 py-2 text-right font-bold">{p.ehi.toFixed(0)}</td>
                      <td className="px-3 py-2 text-xs text-orange-600">
                        {p.risk_rising && "⚠ Rising "}
                        {p.data_gaps.length > 0 && "⚠ Gap"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Patient drawer — slides in from right */}
      {selectedPatient && (
        <div className="w-96 border-l border-gray-200 bg-white shadow-lg flex-shrink-0 overflow-hidden">
          <PatientDrawer patient={selectedPatient} onClose={() => setSelectedPatient(null)} />
        </div>
      )}
    </div>
  );
}
