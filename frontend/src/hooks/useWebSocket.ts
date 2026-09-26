import { useEffect, useRef, useState } from "react";
import type { PatientScore } from "../types";

interface WsMessage {
  type: string;
  data: PatientScore[];
  timestamp: string;
}

export function useUnitWebSocket(unitId: string) {
  const [patients, setPatients] = useState<PatientScore[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/unit/${unitId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      const msg: WsMessage = JSON.parse(e.data as string);
      if (msg.type === "scores_update") setPatients(msg.data);
    };

    return () => ws.close();
  }, [unitId]);

  return { patients, connected };
}
