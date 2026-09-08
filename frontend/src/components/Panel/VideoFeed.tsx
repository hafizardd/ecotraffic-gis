"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { API_BASE } from "@/services/api"

interface VideoFeedProps {
    cameraId: string;
}

const INITIAL_BACKOFF = 1000;
const MAX_BACKOFF = 30000;

type StreamStatus = "loading" | "streaming" | "error";

// Annotated MJPEG display: the tracker bakes boxes + track IDs into each
// frame, so this component is just an <img> — no canvas, no HLS, no WebSocket.
export default function VideoFeed({ cameraId }: VideoFeedProps) {
    const [status, setStatus] = useState<StreamStatus>("loading");
    const [reloadKey, setReloadKey] = useState(0);
    const backoffRef = useRef(INITIAL_BACKOFF);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const streamUrl = API_BASE
        ? `${API_BASE}/api/cameras/${cameraId}/tracked.mjpg${
            reloadKey > 0 ? `?_t=${reloadKey}` : ""
        }`
        : null;

    const scheduleRetry = useCallback(() => {
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
            setStatus("loading");
            setReloadKey((k) => k + 1);
        }, backoffRef.current);
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF);
    }, []);

    useEffect(() => {
        return () => { if (timerRef.current) clearTimeout(timerRef.current); };
    }, []);

    const handleLoad = useCallback(() => {
        setStatus("streaming");
        backoffRef.current = INITIAL_BACKOFF;
    }, []);

    const handleError = useCallback(() => {
        setStatus((prev) => {
            if (prev !== "error") scheduleRetry();
            return "error";
        });
    }, [scheduleRetry]);

    return (
        <div className="video-frame" style={{ position: "relative" }}>
            {status === "loading" && (
                <div className="video-loading">
                    <span className="loading-spinner" />
                    Menghubungkan ke kamera...
                </div>
            )}
            {status === "error" && (
                <div className="video-error" role="status">
                    <strong>Stream tidak tersedia</strong>
                    <span>Mencoba menghubungkan kembali...</span>
                </div>
            )}
            {streamUrl && (
                // Key on cameraId so switching cameras resets the stream.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                    key={cameraId}
                    src={streamUrl}
                    className="video-element"
                    alt={`Tracked CCTV ${cameraId}`}
                    onLoad={handleLoad}
                    onError={handleError}
                    style={{ display: status === "streaming" ? "block" : "none" }}
                />
            )}
        </div>
    )
}
