import { useEffect, useState } from "react";
import { api } from "../../api/client";

interface Props {
  onClose: () => void;
}

// "07:00-07:45 · Room 114 · …" starts a new schedule block
const BLOCK_HEADER = /^\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}/;

export function PtPlanModal({ onClose }: Props) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<"streaming" | "done" | "error">("streaming");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    api
      .streamPtPlan((chunk) => setText((t) => t + chunk), controller.signal)
      .then(() => setStatus("done"))
      .catch((e: Error) => {
        if (controller.signal.aborted) return;
        setError(e.message);
        setStatus("error");
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);

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
              Top-risk residents · generated with Bedrock
              {status === "streaming" && <span className="ml-2 text-blue-500">● writing…</span>}
            </p>
          </div>
          <button onClick={onClose} className="rounded-md px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close">
            ✕
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4 text-sm leading-relaxed text-slate-700">
          {lines.length === 0 && status === "streaming" && (
            <p className="text-slate-400">Reviewing the highest-risk residents…</p>
          )}
          {lines.map((line, i) =>
            BLOCK_HEADER.test(line) ? (
              <p key={i} className={`font-semibold text-slate-900 ${i > 0 ? "mt-4" : ""}`}>{line}</p>
            ) : line.startsWith("Focus:") ? (
              <p key={i} className="text-xs text-blue-700">{line}</p>
            ) : line.startsWith("Handoff:") ? (
              <p key={i} className="mt-5 rounded-lg bg-amber-50 p-3 text-amber-900">{line}</p>
            ) : (
              <p key={i} className="pl-3">{line}</p>
            )
          )}
          {error && <p className="mt-3 text-red-600">Couldn't generate the plan: {error}</p>}
        </div>

        <div className="border-t border-slate-200 px-5 py-2 text-[11px] text-slate-400">
          AI-generated draft — review clinically before use.
        </div>
      </div>
    </div>
  );
}
