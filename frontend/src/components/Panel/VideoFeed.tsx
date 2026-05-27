"use client"

import { useEffect, useRef, useState } from "react"
import Hls from "hls.js"

interface VideoFeedProps {
    streamUrl: string;
}

export default function VideoFeed({ streamUrl }: VideoFeedProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isMuted, setIsMuted] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        let hls: Hls | null = null;

        if (Hls.isSupported()) {
            hls = new Hls({
                enableWorker: true,
                lowLatencyMode: true,
            })

            hls.loadSource(streamUrl);
            hls.attachMedia(video);
            hls.on(Hls.Events.ERROR, (_, data) => {
                if (data.fatal) {
                    setError("Failed to load video stream");
                    hls?.destroy();
                }
            });
        } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
            // Safari
            video.src = streamUrl;
        } else {
            setError("HLS not supported in this browser");
        }

        video.muted = isMuted;
        video.play().catch(() => {});
        
        return () => {
            hls?.destroy();
        };
    }, [streamUrl, isMuted])

    const toggleMute = () => {
        if (videoRef.current) {
            videoRef.current.muted = !isMuted;
            setIsMuted(!isMuted);
        }
    };

    if (error) {
        return (
             <div className="flex items-center justify-center h-48 bg-zinc-900 text-zinc-400 text-sm">
                {error}
            </div>
        )
    }

    return (
        <div className="relative bg-black">
            <video
                ref={videoRef}
                className="w-full aspect-video"
                muted={isMuted}
                autoPlay
                playsInline
            />
            <button
                onClick={toggleMute}
                className="absolute bottom-2 right-2 px-2 py-1 text-xs bg-black/60 text-white rounded hover:bg-black/80"
            >
                {isMuted ? "Unmute" : "Mute"}
            </button>
        </div>
    )
}