"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { API_BASE } from "@/services/api"
import Skeleton from "@/components/ui/Skeleton"

interface VideoFeedProps {
    cameraId: string;
    onStatusChange?: (status: StreamStatus) => void;
}

const INITIAL_BACKOFF = 1000;
const MAX_BACKOFF = 30000;

type StreamStatus = "loading" | "streaming" | "error";

// Annotated MJPEG display: the tracker bakes boxes + track IDs into each
// frame, so this component is just an <img>: no canvas, no HLS, no WebSocket.
export default function VideoFeed({ cameraId, onStatusChange }: VideoFeedProps) {
    const [status, setStatus] = useState<StreamStatus>("loading");
    const [reloadKey, setReloadKey] = useState(0);
    const [isVisible, setIsVisible] = useState(() =>
        typeof document === "undefined" || !document.hidden
    );
    const backoffRef = useRef(INITIAL_BACKOFF);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const streamUrl = isVisible && API_BASE
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
        onStatusChange?.("loading");
        const updateVisibility = () => {
            const visible = !document.hidden;
            setIsVisible(visible);
            if (visible) setReloadKey((key) => key + 1);
        };
        document.addEventListener("visibilitychange", updateVisibility);
        return () => {
            document.removeEventListener("visibilitychange", updateVisibility);
            if (timerRef.current) clearTimeout(timerRef.current);
        };
    }, [cameraId, onStatusChange]);

    const handleLoad = useCallback(() => {
        setStatus("streaming");
        onStatusChange?.("streaming");
        backoffRef.current = INITIAL_BACKOFF;
    }, [onStatusChange]);

    const handleError = useCallback(() => {
        onStatusChange?.("error");
        setStatus((prev) => {
            if (prev !== "error") scheduleRetry();
            return "error";
        });
    }, [onStatusChange, scheduleRetry]);

    return (
        <div className="relative aspect-video overflow-hidden rounded-[var(--radius-md)] border border-[var(--contour-strong)] bg-[var(--canvas)]">
            {status === "loading" && (
                <div className="absolute inset-0 flex items-center justify-center gap-2 bg-[var(--canvas)] text-[10px] text-[var(--secondary)]" role="status" aria-label="Menghubungkan stream CCTV">
                    <Skeleton height="100%" width="100%" radius={0} />
                </div>
            )}
            {status === "error" && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-[var(--canvas)] px-4 text-center [&>strong]:text-[12px] [&>strong]:text-[#fca5a5] [&>span]:text-[10px] [&>span]:text-[var(--muted)]" role="status">
                    <strong>Stream tidak tersedia</strong>
                    <span>Mencoba menghubungkan kembali…</span>
                </div>
            )}
            {streamUrl && (
                // Key on cameraId so switching cameras resets the stream.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                    key={cameraId}
                    src={streamUrl}
                    className={`h-full w-full object-cover ${status === "streaming" ? "block" : "hidden"}`}
                    alt={`Tracked CCTV ${cameraId}`}
                    decoding="async"
                    fetchPriority="low"
                    onLoad={handleLoad}
                    onError={handleError}
                />
            )}
        </div>
    )
}
