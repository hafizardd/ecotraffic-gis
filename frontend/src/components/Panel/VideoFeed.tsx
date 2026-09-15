"use client"

import { useEffect, useRef, useState } from "react"
import { Maximize2, X } from "lucide-react"
import { API_BASE } from "@/services/api"
import { readMjpeg } from "@/services/mjpeg"
import { reportTelemetry } from "@/services/telemetry"

export type StreamStatus = "loading" | "streaming" | "delayed" | "error";

export default function VideoFeed({ cameraId, onStatusChange }: {
    cameraId: string; onStatusChange?: (status: StreamStatus) => void;
}) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const dialogRef = useRef<HTMLDialogElement>(null);
    const expandRef = useRef<HTMLButtonElement>(null);
    const [expanded, setExpanded] = useState(false);
    const [status, setStatus] = useState<StreamStatus>('loading');
    const [gap, setGap] = useState(0);
    const [hasFrame, setHasFrame] = useState(false);
    useEffect(() => { onStatusChange?.(status); }, [status, onStatusChange]);

    // Promote the same canvas to the top layer; keep one connection and decoder.
    useEffect(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;
        dialog.close();
        if (expanded) {
            const overflow = document.body.style.overflow;
            document.body.style.overflow = 'hidden';
            dialog.showModal();
            return () => { document.body.style.overflow = overflow; dialog.close(); };
        }
        dialog.show();
    }, [expanded]);

    useEffect(() => {
        let disposed = false;
        let controller: AbortController | undefined;
        let retry: ReturnType<typeof setTimeout> | undefined;
        let backoff = 1000;
        let lastFrame = performance.now();
        let waitingSince = lastFrame;
        let received = false;
        let lastId: string | undefined;
        let attemptStarted = lastFrame;
        queueMicrotask(() => { if (!disposed) setHasFrame(false); });
        canvasRef.current?.getContext('2d')?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
        let failed = false;
        let timeoutReported = false;
        const connect = async () => {
            if (disposed || document.hidden) return;
            const attempt = new AbortController();
            controller = attempt;
            waitingSince = performance.now(); attemptStarted = waitingSince;
            timeoutReported = false; failed = false;
            setStatus(received ? 'delayed' : 'loading');
            try {
                if (!API_BASE) throw new Error('API unavailable');
                const response = await fetch(`${API_BASE}/api/cameras/${encodeURIComponent(cameraId)}/tracked.mjpg`, { signal: attempt.signal, cache: 'no-store' });
                if (!response.ok || !response.body) throw new Error('Stream unavailable');
                await readMjpeg(response.body, async (jpeg, metadata) => {
                    if (metadata.id && metadata.id === lastId) return;
                    const bitmap = await createImageBitmap(new Blob([jpeg], { type: 'image/jpeg' }));
                    try {
                        if (disposed || attempt.signal.aborted) return;
                        const canvas = canvasRef.current;
                        const context = canvas?.getContext('2d');
                        if (!canvas || !context) throw new Error('Video rendering unavailable');
                        if (canvas.width !== bitmap.width) canvas.width = bitmap.width;
                        if (canvas.height !== bitmap.height) canvas.height = bitmap.height;
                        context.drawImage(bitmap, 0, 0);
                        if (!received) reportTelemetry('video_load_event', 'video', 'ok', performance.now() - waitingSince);
                        lastId = metadata.id;
                        received = true; lastFrame = performance.now() - metadata.ageMs;
                        if (metadata.ageMs < 3000) backoff = 1000;
                        setGap(Math.floor(metadata.ageMs / 1000));
                        setHasFrame(true); setStatus(metadata.ageMs >= 3000 ? 'delayed' : 'streaming');
                    } finally { bitmap.close(); }
                });
            } catch {
                if (disposed || attempt.signal.aborted) return;
                failed = true; setStatus('error');
                reportTelemetry('video_error', 'video', 'error', performance.now() - waitingSince);
                retry = setTimeout(connect, backoff); backoff = Math.min(backoff * 2, 30000);
            }
        };
        const timer = setInterval(() => {
            if (document.hidden) return;
            const elapsed = performance.now() - lastFrame;
            setGap(Math.floor(elapsed / 1000));
            if (!failed && elapsed >= 3000) setStatus('delayed');
            if (!timeoutReported && elapsed >= 15000) {
                reportTelemetry('video_loading_timeout', 'video', 'timeout', elapsed); timeoutReported = true;
            }
            if (!failed && elapsed >= 30000 && performance.now() - attemptStarted >= 30000) {
                controller?.abort(); failed = true; setStatus('error');
                retry = setTimeout(connect, backoff); backoff = Math.min(backoff * 2, 30000);
            }
        }, 1000);
        const visibility = () => { controller?.abort(); clearTimeout(retry); if (!document.hidden) void connect(); };
        document.addEventListener('visibilitychange', visibility);
        void connect();
        return () => { disposed = true; controller?.abort(); clearTimeout(retry); clearInterval(timer); document.removeEventListener('visibilitychange', visibility); };
    }, [cameraId]);

    const close = () => { setExpanded(false); requestAnimationFrame(() => expandRef.current?.focus()); };
    return <div className="relative aspect-video">
        <dialog ref={dialogRef} aria-label={`Video CCTV ${cameraId}`} onCancel={event => { event.preventDefault(); close(); }}
            onClick={event => { if (expanded && event.target === event.currentTarget) close(); }}
            className={expanded ? 'fixed inset-0 m-auto h-fit max-h-[90dvh] w-[min(1100px,94vw)] max-w-none overflow-visible border-0 bg-transparent p-0 text-white backdrop:bg-black/80' : 'relative inset-auto m-0 block w-full max-w-none border-0 bg-transparent p-0 text-white'}>
            <div className="relative overflow-hidden rounded-md border border-(--contour-strong) bg-black">
                <canvas ref={canvasRef} aria-label={`CCTV beranotasi ${cameraId}`} role="img" className={`${expanded ? 'max-h-[85dvh]' : ''} aspect-video w-full object-contain`} />
                {!hasFrame && <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-(--canvas) px-6 text-center text-sm text-(--secondary)">Menunggu frame beranotasi…</div>}
                {status !== 'streaming' && <div role="status" className="absolute top-3 left-3 right-14 rounded-md bg-black/80 p-3 text-xs text-amber-200">
                    {status === 'loading' ? 'Menghubungkan CCTV…' : status === 'error' ? 'Menyambungkan ulang video…' : `Video tertunda · ${gap} detik tanpa frame baru`}
                    {status === 'delayed' && <span className="mt-1 block text-white/80">Menunggu frame dan anotasi yang sesuai.{hasFrame ? ' Gambar terakhir tetap ditampilkan.' : ''}</span>}
                </div>}
                {expanded ? <button type="button" autoFocus onClick={close} aria-label="Tutup video besar" className="absolute top-3 right-3 rounded-md bg-black/80 p-2 focus-visible:outline-2 focus-visible:outline-white"><X size={20} /></button>
                    : <button ref={expandRef} type="button" onClick={() => setExpanded(true)} aria-label="Perbesar video CCTV" className="absolute right-3 bottom-3 rounded-md bg-black/80 p-2 hover:bg-black focus-visible:outline-2 focus-visible:outline-white"><Maximize2 size={20} /></button>}
            </div>
        </dialog>
    </div>
}
