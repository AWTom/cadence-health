import { useEffect, useRef } from "react";
import type { StreamState } from "../../hooks/usePtPlan";

interface Props {
  plan: StreamState;
  report: StreamState;
  onGenerateReport: () => void;
  onClose: () => void;
}

// "07:00-07:45 · Room 114 · …" starts a new schedule block
const BLOCK_HEADER = /^\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}/;

const toLines = (text: string) => text.split("\n").map((l) => l.trim()).filter(Boolean);

function PlanLine({ line, first }: { line: string; first: boolean }) {
  if (line.startsWith("Handoff:")) return <p className="mt-5 rounded-lg bg-amber-50 p-3 text-amber-900">{line}</p>;
  if (BLOCK_HEADER.test(line)) return <p className={`font-semibold text-slate-900 ${first ? "" : "mt-4"}`}>{line}</p>;
  if (line.startsWith("Focus:")) return <p className="text-xs text-blue-700">{line}</p>;
  return <p className="pl-3">{line}</p>;
}

function ReportLine({ line }: { line: string }) {
  if (line.startsWith("›")) return <p className="text-xs italic text-slate-400">{line}</p>;
  if (line === "Administrative Cost Savings Report") return <p className="mt-2 font-bold text-slate-900">{line}</p>;
  if (line.startsWith("Totals:")) return <p className="mt-3 rounded-lg bg-emerald-50 p-3 font-semibold text-emerald-900">{line}</p>;
  if (line.startsWith("Summary:") || line === "By resident:") return <p className="mt-2 text-slate-800">{line}</p>;
  if (line.startsWith("Assumptions:") || line.startsWith("Caveat:")) return <p className="mt-2 text-xs text-slate-500">{line}</p>;
  return <p className="pl-3">{line}</p>;
}

export function PtPlanModal({ plan, report, onGenerateReport, onClose }: Props) {
  const reportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Bring the report into view when it starts
  useEffect(() => {
    if (report.status === "streaming" && !report.text) reportRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [report.status, report.text]);

  const planLines = toLines(plan.text);
  const reportLines = toLines(report.text);
  const canReport = plan.status === "done" && report.status !== "streaming";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pt-plan-title"
        className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <div>
            <h2 id="pt-plan-title" className="text-base font-bold text-slate-900">PT Shift Plan · 07:00–15:30</h2>
            <p className="text-xs text-slate-400">
              Top-risk residents · {plan.fallback ? "sample plan" : "generated with Bedrock"}
              {plan.status === "streaming" && <span className="ml-2 text-blue-500">● writing…</span>}
            </p>
          </div>
          <button onClick={onClose} className="rounded-md px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close">
            ✕
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4 text-sm leading-relaxed text-slate-700">
          {planLines.length === 0 && plan.status === "streaming" && (
            <p className="text-slate-400">Reviewing the highest-risk residents…</p>
          )}
          {planLines.map((line, i) => <PlanLine key={i} line={line} first={i === 0} />)}
          {plan.error && <p className="mt-3 text-red-600">Couldn't generate the plan: {plan.error}</p>}

          {report.status !== "idle" && (
            <div ref={reportRef} className="mt-6 border-t border-slate-200 pt-4">
              {reportLines.map((line, i) => <ReportLine key={i} line={line} />)}
              {report.status === "streaming" && <p className="mt-1 text-xs text-blue-500">● working…</p>}
              {report.error && <p className="mt-3 text-red-600">Couldn't generate the report: {report.error}</p>}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-5 py-2.5">
          <p className="text-[11px] text-slate-400">
            {plan.fallback
              ? "Sample plan shown — the live planner is unavailable right now."
              : "AI-generated draft — review clinically before use."}
          </p>
          <button
            onClick={onGenerateReport}
            disabled={!canReport}
            className="shrink-0 rounded-lg border border-emerald-600 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300 disabled:hover:bg-transparent"
          >
            {report.status === "done" ? "Rerun cost savings report" : "Administrative cost savings report"}
          </button>
        </div>
      </div>
    </div>
  );
}
