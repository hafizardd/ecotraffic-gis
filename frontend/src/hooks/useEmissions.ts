import { WS_URL } from "@/services/api";
import { EmissionUpdate } from "@/types";
import { useCallback, useEffect, useRef, useState } from "react";

const MAX_BACKOFF = 30000;
const INITIAL_BACKOFF = 1000;

export default function useEmissions() {
    const [emissionMap, setEmissionMap] = useState<Map<string, EmissionUpdate>>(new Map());
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
                const data: EmissionUpdate = JSON.parse(event.data);
                setEmissionMap((prev) => {
                    const next = new Map(prev);
                    next.set(data.camera_id, data);
                    return next;
                });
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
    
    return emissionMap;
}