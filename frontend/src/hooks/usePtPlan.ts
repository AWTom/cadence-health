import { useCallback, useEffect, useRef, useState } from "react";
import { api, HttpError } from "../api/client";
import { buildMockPlan, streamText } from "../components/PtPlanModal/mockPlan";
import type { PatientScore } from "../types";

export interface StreamState {
  text: string;
  status: "idle" | "streaming" | "done" | "error";
  error?: string;
  fallback?: boolean;
}

const IDLE: StreamState = { text: "", status: "idle" };

/**
 * Owns the PT plan and its savings report so they survive the modal closing.
 * Streams keep running in the background; regenerating aborts the previous run.
 */
export function usePtPlan(patients: PatientScore[]) {
  const [plan, setPlan] = useState<StreamState>(IDLE);
  const [report, setReport] = useState<StreamState>(IDLE);
  const planCtl = useRef<AbortController | null>(null);
  const reportCtl = useRef<AbortController | null>(null);
  const patientsRef = useRef(patients);
  patientsRef.current = patients;

  useEffect(() => () => {
    planCtl.current?.abort();
    reportCtl.current?.abort();
  }, []);

  const generatePlan = useCallback(() => {
    planCtl.current?.abort();
    reportCtl.current?.abort();
    const ctl = new AbortController();
    planCtl.current = ctl;
    setReport(IDLE);
    setPlan({ text: "", status: "streaming" });
    const append = (chunk: string) => setPlan((s) => ({ ...s, text: s.text + chunk }));

    api.streamPtPlan(append, ctl.signal)
      .catch(async (e: Error) => {
        if (ctl.signal.aborted) return;
        if (!(e instanceof HttpError && e.status === 404)) throw e;
        // Endpoint missing (e.g. backend not redeployed) — show a sample plan instead
        setPlan({ text: "", status: "streaming", fallback: true });
        await streamText(buildMockPlan(patientsRef.current), append, ctl.signal);
      })
      .then(() => {
        if (!ctl.signal.aborted) setPlan((s) => ({ ...s, status: "done" }));
      })
      .catch((e: Error) => {
        if (!ctl.signal.aborted) setPlan((s) => ({ ...s, status: "error", error: e.message }));
      });
  }, []);

  const generateReport = useCallback((planText: string) => {
    reportCtl.current?.abort();
    const ctl = new AbortController();
    reportCtl.current = ctl;
    setReport({ text: "", status: "streaming" });

    api.streamSavingsReport(planText, (chunk) => setReport((s) => ({ ...s, text: s.text + chunk })), ctl.signal)
      .then(() => {
        if (!ctl.signal.aborted) setReport((s) => ({ ...s, status: "done" }));
      })
      .catch((e: Error) => {
        if (!ctl.signal.aborted) setReport((s) => ({ ...s, status: "error", error: e.message }));
      });
  }, []);

  return { plan, report, generatePlan, generateReport };
}
