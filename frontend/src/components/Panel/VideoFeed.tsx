"use client"

import { useEffect, useRef, useState } from "react"
import { Volume2, VolumeX } from "lucide-react"
import Hls from "hls.js"
import { useEmissionsContext } from "@/context/EmissionsContext"
import { API_BASE } from "@/services/api"
import { TrackUpdate } from "@/types"

interface VideoFeedProps {
    streamUrl: string;
    cameraId: string;
}

const ROI_FILL = "rgba(0,255,0,0.31)";
const ROI_STROKE = "#00ff00";

export default function VideoFeed({ streamUrl, cameraId }: VideoFeedProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const { trackMap } = useEmissionsContext();
    const [isMuted, setIsMuted] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [roiFallback, setRoiFallback] = useState<[number, number][] | null>(null);

    const [retryCount, setRetryCount] = useState(0);
    const posterUrl = API_BASE ? `${API_BASE}/api/cameras/${cameraId}/snapshot` : null;
    // Backend-proxied HLS (injects Referer + same-origin, fixing 403/CORS on
    // cctvjss). Proxy-only: direct streamUrl always fails the same way.
    const proxiedUrl = API_BASE ? `${API_BASE}/api/cameras/${cameraId}/live/playlist.m3u8` : streamUrl;
    const [posterVisible, setPosterVisible] = useState(true);
    const [posterFailed, setPosterFailed] = useState(false);
    const [slowNotice, setSlowNotice] = useState(false);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        let hls: Hls | null = null;
        let cancelled = false;
        // Non-destructive stall notice: overlays a hint but keeps the player
        // alive so a slow-but-working stream can still recover on its own.
        timeoutRef.current = setTimeout(() => {
            if (!cancelled && video.readyState < 2) {
                setSlowNotice(true);
            }
        }, 15000);
        let retries = 0;
        const MAX_RETRIES = 5;
        const retryDelays = [1000, 2000, 4000, 8000, 8000];
        setError(null);
        setIsLoading(true);
        setSlowNotice(false);
        setPosterVisible(true);
        setPosterFailed(false);

        const startPlayback = () => {
            if (cancelled) return;
            video.play().catch(() => {});
        };

        if (Hls.isSupported()) {
            hls = new Hls({
                enableWorker: true,
                lowLatencyMode: true,
                // Fast-start profile: buffer little, start near live edge, start low.
                maxBufferLength: 8,
                maxMaxBufferLength: 15,
                liveSyncDurationCount: 2,
                maxLiveSyncPlaybackRate: 1.5,
                capLevelToPlayerSize: true,
                abrEwmaDefaultEstimate: 500000,
                fragLoadingMaxRetry: 4,
                manifestLoadingMaxRetry: 2,
                levelLoadingMaxRetry: 3,
                fragLoadingRetryDelay: 500,
            })

            hls.loadSource(proxiedUrl);
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, startPlayback);
            hls.on(Hls.Events.ERROR, (_, data) => {
                if (cancelled || !data.fatal) return;
                if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                    try {
                        hls?.recoverMediaError();
                        startPlayback();
                        return;
                    } catch { /* fall through to retry */ }
                }
                if (retries < MAX_RETRIES) {
                    // Non-destructive retry: keep hls alive so the poster stays
                    // underneath and a slow proxy can still recover on its own.
                    const delay = retryDelays[retries] ?? 4000;
                    retries += 1;
                    setTimeout(() => {
                        if (cancelled) return;
                        try {
                            hls?.startLoad();
                            startPlayback();
                        } catch {
                            setError("Failed to load video stream");
                        }
                    }, delay);
                    return;
                }
                setError("Failed to load video stream");
                try { hls?.destroy(); } catch { /* noop */ }
            });
        } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
            // Safari
            video.src = proxiedUrl;
            startPlayback();
        } else {
            setError("HLS not supported in this browser");
        }

        return () => {
            cancelled = true;
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            try { hls?.destroy(); } catch { /* noop */ }
        };
    }, [proxiedUrl, retryCount])

    // Fallback ROI when the tracker hasn't published yet.
    useEffect(() => {
        if (trackMap.get(cameraId)?.roi) return;
        let cancelled = false;
        fetch(`${API_BASE}/api/cameras/${cameraId}/tracks`)
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => { if (!cancelled && data?.roi) setRoiFallback(data.roi); })
            .catch(() => {});
        return () => { cancelled = true; };
    }, [cameraId, trackMap])

    // Canvas overlay: filled ROI + track boxes with IDs.
    useEffect(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas) return;
        let raf = 0;

        const draw = () => {
            raf = requestAnimationFrame(draw);
            const w = video.clientWidth;
            const h = video.clientHeight;
            if (!w || !h) return;
            if (canvas.width !== w || canvas.height !== h) {
                canvas.width = w;
                canvas.height = h;
            }
            const ctx = canvas.getContext("2d");
            if (!ctx) return;
            ctx.clearRect(0, 0, w, h);

            const update: TrackUpdate | undefined = trackMap.get(cameraId);
            const roi = update?.roi ?? roiFallback;
            if (roi && roi.length >= 3) {
                ctx.beginPath();
                roi.forEach(([xr, yr], i) => {
                    const x = xr * w;
                    const y = yr * h;
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                });
                ctx.closePath();
                ctx.fillStyle = ROI_FILL;
                ctx.fill();
                ctx.strokeStyle = ROI_STROKE;
                ctx.lineWidth = 2;
                ctx.stroke();
            }
            if (!update) return;
            for (const t of update.tracks) {
                const x1 = t.x1 * w;
                const y1 = t.y1 * h;
                const x2 = t.x2 * w;
                const y2 = t.y2 * h;
                ctx.globalAlpha = t.inside_roi ? 1 : 0.35;
                ctx.strokeStyle = t.inside_roi ? "#00ff00" : "#808080";
                ctx.lineWidth = 2;
                ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
                ctx.globalAlpha = 1;
                const label = `${t.id != null ? `#${t.id} ` : ""}${t.cls} ${t.conf.toFixed(2)}`;
                ctx.font = "12px sans-serif";
                const tw = ctx.measureText(label).width;
                ctx.fillStyle = t.inside_roi ? "#00ff00" : "#808080";
                ctx.fillRect(x1, Math.max(0, y1 - 18), tw + 8, 18);
                ctx.fillStyle = "#000";
                ctx.fillText(label, x1 + 4, Math.max(12, y1 - 5));
            }
        };
        raf = requestAnimationFrame(draw);
        return () => cancelAnimationFrame(raf);
    }, [cameraId, trackMap, roiFallback]);

    useEffect(() => {
        if (videoRef.current) videoRef.current.muted = isMuted;
    }, [isMuted]);

    const toggleMute = () => {
        if (videoRef.current) {
            videoRef.current.muted = !isMuted;
            setIsMuted(!isMuted);
        }
    };

    if (error) {
        return (
            <div className="flex items-center justify-center h-48 bg-zinc-900 text-zinc-400 text-sm">
                <div className="video-error"><strong>Stream tidak tersedia</strong><span>{error}</span></div>
                <button
                    onClick={() => { setError(null); setIsLoading(true); setRetryCount((c) => c + 1); }}
                    className="video-control"
                    style={{ position: "static", marginLeft: 12 }}
                >
                    Coba lagi
                </button>
            </div>
        )
    }

    const trackCount = trackMap.get(cameraId)?.tracks.filter((t) => t.inside_roi).length ?? 0;

    return (
        <div className="video-frame" style={{ position: "relative" }}>
            {isLoading && <div className="video-loading"><span className="loading-spinner" />Menghubungkan ke kamera...</div>}
            {posterVisible && posterUrl && !posterFailed && (
                // Instant still frame while HLS buffers — hides on first video frame.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                    src={posterUrl}
                    alt="Frame terakhir kamera"
                    style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", pointerEvents: "none" }}
                    onError={() => setPosterFailed(true)}
                />
            )}
            <video
                ref={videoRef}
                className="video-element"
                muted={isMuted}
                autoPlay
                playsInline
                preload="metadata"
                onPlaying={() => {
                    setIsLoading(false);
                    setSlowNotice(false);
                    setPosterVisible(false);
                    if (timeoutRef.current) clearTimeout(timeoutRef.current);
                }}
            />
            {slowNotice && !error && (
                <div
                    style={{ position: "absolute", bottom: 8, left: 8, right: 8, background: "rgba(0,0,0,0.65)", color: "#ffd166", fontSize: 12, padding: "6px 10px", borderRadius: 4, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}
                    role="status"
                >
                    <span>Stream lambat — masih mencoba memuat…</span>
                    <button
                        onClick={() => { setError(null); setIsLoading(true); setSlowNotice(false); setRetryCount((c) => c + 1); }}
                        style={{ background: "#ffd166", color: "#000", border: 0, borderRadius: 4, padding: "2px 10px", cursor: "pointer", fontSize: 12 }}
                    >
                        Muat ulang
                    </button>
                </div>
            )}
            <canvas
                ref={canvasRef}
                style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
            />
            <div
                style={{ position: "absolute", top: 8, left: 8, background: "rgba(0,0,0,0.6)", color: "#fff", fontSize: 12, padding: "2px 8px", borderRadius: 4, pointerEvents: "none" }}
                aria-live="polite"
            >
                ROI tracking • {trackCount} di dalam ROI
            </div>
            <button
                onClick={toggleMute}
                className="video-control"
                aria-label={isMuted ? "Aktifkan suara" : "Bisukan suara"}
                aria-pressed={!isMuted}
            >
                {isMuted ? <VolumeX aria-hidden="true" /> : <Volume2 aria-hidden="true" />}
            </button>
        </div>
    )
}
