import { WS_URL } from "@/services/api";
import { EmissionUpdate, SegmentUpdate } from "@/types";
import { useCallback, useEffect, useRef, useState } from "react";

const MAX_BACKOFF = 30000;
const INITIAL_BACKOFF = 1000;

export default function useEmissions() {
    const [emissionMap, setEmissionMap] = useState<Map<string, EmissionUpdate>>(new Map());
    const [segmentMap, setSegmentMap] = useState<Map<string, SegmentUpdate["data"]>>(new Map());
    const wsRef = useRef<WebSocket | null>(null);

    const connect = useCallback(() => {
        let cancelled = false;
        let reconnectTimer: ReturnType<typeof setTimeout>;
        let backoff = INITIAL_BACKOFF;

        function attemptConnect() {
            if (cancelled) return;
            const ws = new WebSocket(`${WS_URL}/ws/emissions`);
            wsRef.current = ws;

            ws.onopen = () => {
                backoff = INITIAL_BACKOFF;
            };
            
            ws.onmessage = (event) => {
                if (cancelled) return;
                try {
                    const data = JSON.parse(event.data) as Partial<EmissionUpdate & SegmentUpdate>;
                    if (data.type === "segment_update" && data.segment_id && data.data) setSegmentMap((prev) => new Map(prev).set(data.segment_id!, data.data!));
                    else if (data.camera_id) setEmissionMap((prev) => new Map(prev).set(data.camera_id!, data as EmissionUpdate));
                } catch { /* Ignore malformed messages. */ }
            };

            ws.onclose = () => {
                if (!cancelled) {
                    reconnectTimer = setTimeout(() => {
                        backoff = Math.min(backoff * 2, MAX_BACKOFF);
                        attemptConnect();
                    }, backoff);
                }
            };

            ws.onerror = () => {
                ws.close();
            };
        }

        attemptConnect();

        return () => {
            cancelled = true;
            clearTimeout(reconnectTimer);
            const ws = wsRef.current;

            if (ws) {
                if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                    ws.close();
                }
                wsRef.current = null;
            }
        };
    }, []);

    useEffect(() => {
        const cleanup = connect();
        return cleanup;
    }, [connect]);
    
    return { emissionMap, segmentMap };
}
