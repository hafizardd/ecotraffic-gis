import { API_BASE, WS_URL, fetchCameraEmissions } from "@/services/api";
import { EmissionUpdate, SegmentUpdate, SegmentUpdateData, TrackUpdate } from "@/types";
import { useEffect, useRef, useState } from "react";

const MAX_BACKOFF = 30000;
const INITIAL_BACKOFF = 1000;

function timestampOf(value: Partial<EmissionUpdate>): number {
    const timestamp = value.updated_at ?? value.processed_at ?? value.captured_at ?? value.timestamp;
    return timestamp ? Date.parse(timestamp) : 0;
}

function segmentTimestampOf(value: SegmentUpdateData): number {
    const timestamp = value.calculated_at ?? value.observed_at;
    return timestamp ? Date.parse(timestamp) : 0;
}

function validCameraMessage(value: unknown): value is EmissionUpdate {
    if (!value || typeof value !== "object") return false;
    const item = value as Partial<EmissionUpdate>;
    return typeof item.camera_id === "string" && typeof item.timestamp === "string";
}

function validSegmentMessage(value: unknown): value is SegmentUpdate {
    if (!value || typeof value !== "object") return false;
    const item = value as Partial<SegmentUpdate>;
    return item.type === "segment_update" && typeof item.segment_id === "string" && !!item.data && typeof item.data === "object";
}

function validTrackMessage(value: unknown): value is TrackUpdate {
    if (!value || typeof value !== "object") return false;
    const item = value as Partial<TrackUpdate>;
    return item.type === "track_update" && typeof item.camera_id === "string" && Array.isArray(item.tracks);
}

export default function useEmissions() {
    const [emissionMap, setEmissionMap] = useState<Map<string, EmissionUpdate>>(new Map());
    const [segmentMap, setSegmentMap] = useState<Map<string, SegmentUpdateData>>(new Map());
    const [trackMap, setTrackMap] = useState<Map<string, TrackUpdate>>(new Map());
    const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
    const [lastMessageAt, setLastMessageAt] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const latestRef = useRef(new Map<string, number>());
    const segmentLatestRef = useRef(new Map<string, number>());

    useEffect(() => {
        let cancelled = false;
        let timer: ReturnType<typeof setTimeout> | undefined;
        let backoff = INITIAL_BACKOFF;

        const hydrate = async () => {
            try {
                if (!API_BASE) throw new Error("API URL is not configured");
                const cameras = await fetch(`${API_BASE}/api/cameras`).then((r) => r.json());
                for (const camera of cameras.features ?? []) {
                    const id = camera.properties.camera_id;
                    const response = await fetchCameraEmissions(id, 1);
                    const latest = response.emissions[0];
                    if (latest) setEmissionMap((prev) => new Map(prev).set(id, { ...latest, camera_id: id, timestamp: latest.timestamp } as EmissionUpdate));
                }
            } catch { setError("Gagal memuat data awal"); }
        };
        void hydrate();

        const connect = () => {
            if (cancelled) return;
            setConnectionStatus("connecting");
            const ws = new WebSocket(`${WS_URL}/ws/emissions`);
            ws.onopen = () => { backoff = INITIAL_BACKOFF; setConnectionStatus("connected"); setError(null); };
            ws.onmessage = (event) => {
                if (cancelled) return;
                try {
                    const data = JSON.parse(event.data) as SegmentUpdate | EmissionUpdate | TrackUpdate;
                    const messageTime = new Date().toISOString();
                    if (validSegmentMessage(data)) {
                        const segment = data as SegmentUpdate;
                        const time = segmentTimestampOf(segment.data);
                        if (time > 0 && time < (segmentLatestRef.current.get(segment.segment_id) ?? 0)) {
                            setLastMessageAt(messageTime);
                            return;
                        }
                        if (time > 0) segmentLatestRef.current.set(segment.segment_id, time);
                        setSegmentMap((prev) => {
                            const existing = prev.get(segment.segment_id) ?? {};
                            const merged: SegmentUpdateData = { ...existing, ...segment.data };
                            return new Map(prev).set(segment.segment_id, merged);
                        });
                    } else if (validTrackMessage(data)) {
                        setTrackMap((prev) => new Map(prev).set(data.camera_id, data));
                    } else if (validCameraMessage(data)) {
                        const time = timestampOf(data);
                        if (time < (latestRef.current.get(data.camera_id) ?? 0)) { setLastMessageAt(messageTime); return; }
                        latestRef.current.set(data.camera_id, time);
                        setEmissionMap((prev) => new Map(prev).set(data.camera_id, data));
                    } else if ((data as { type?: string }).type !== "system_status") {
                        setError("Pesan realtime tidak valid");
                        return;
                    }
                    setLastMessageAt(messageTime);
                } catch { setError("Pesan realtime tidak valid"); }
            };
            ws.onclose = () => { if (!cancelled) { setConnectionStatus("disconnected"); timer = setTimeout(() => { backoff = Math.min(backoff * 2, MAX_BACKOFF); connect(); }, backoff); } };
            ws.onerror = () => ws.close();
        };
        connect();
        return () => { cancelled = true; if (timer) clearTimeout(timer); };
    }, []);
    return { emissionMap, segmentMap, trackMap, connectionStatus, lastMessageAt, error };
}
