import { WS_URL } from "@/services/api";
import { CameraFeature, EmissionUpdate } from "@/types";
import { useEffect, useRef, useState } from "react";

export default function useEmissionsWebSocket(cameras: CameraFeature[]) {
    const [emissionMap, setEmissionMap] = useState<Map<string, number>>(new Map());
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (cameras.length === 0) return;

        let cancelled = false;
        let reconnectTimer: ReturnType<typeof setTimeout>;

        function connect() {
            if (cancelled) return;

            const ws = new WebSocket(`${WS_URL}/ws/emissions`);
            wsRef.current = ws;

            ws.onopen = () => {
                // Connection established — nothing to do, but having this
                // handler prevents the close handler firing prematurely
                // in some browsers when the socket is replaced.
                console.log("✅ WebSocket connected");
            };

            ws.onmessage = (event) => {
                if (cancelled) return;
                const data: EmissionUpdate = JSON.parse(event.data);
                console.log("📩 Received:", event.data);
                setEmissionMap((prev) => {
                    const next = new Map(prev);
                    next.set(data.camera_id, data.total_co_g_per_min);
                    console.log(next)
                    return next;
                });
            };

            ws.onclose = () => {
                if (!cancelled) {
                    reconnectTimer = setTimeout(connect, 3000);
                }
            };

            ws.onerror = () => {
                // Let onclose handle the reconnect; avoid double-reconnect
                ws.close();
            };
        }

        connect();

        return () => {
            cancelled = true;
            clearTimeout(reconnectTimer);
            const ws = wsRef.current;
            if (ws) {
                // Only close if the socket is open or connecting —
                // avoids the "closed before established" error
                if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                    ws.close();
                }
                wsRef.current = null;
            }
        };
    }, [cameras.length]); // ← depend on length, not the array reference

    return emissionMap;
}