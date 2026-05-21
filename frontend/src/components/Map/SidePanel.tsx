"use client";

import { CameraFeature, EmissionUpdate } from "@/types";
import VideoFeed from "./VideoFeed";
import EmissionStats from "./EmissionStats";
import VehicleCount from "./VehicleCount";
import { useEmissionsContext } from "@/context/EmissionsContext";

interface SidePanelProps {
    camera: CameraFeature | null;
    onClose: () => void;
}

export default function SidePanel({ camera, onClose }: SidePanelProps) {
    const emissionMap = useEmissionsContext();
    const liveEmission = camera
        ? emissionMap.get(camera.properties.camera_id) ?? null
        : null;

    if (!camera) return null;

    return (
        <div
            className="fixed top-0 right-0 h-full w-100 bg-white dark:bg-zinc-900 shadow-2xl transform transition-transform duration-300 ease-in-out z-[9999]"
        >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-700">
                <h2 className="text-lg font-semibold">{camera.properties.name}</h2>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800"
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            {/* Content */}
            <div className="overflow-y-auto h-[calc(100%-60px)]">
                {/* Section 1: Live Video */}
                <div className="border-b border-zinc-200 dark:border-zinc-700">
                    <VideoFeed streamUrl={camera.properties.stream_url} />
                </div>
                {/* Section 2: Emission Stats */}
                <div className="border-b border-zinc-200 dark:border-zinc-700">
                    <h3 className="px-4 pt-4 pb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
                        Current Emissions
                    </h3>
                    <EmissionStats
                        cameraId={camera.properties.camera_id}
                    />
                </div>
                {/* Section 3: Vehicle Count */}
                <div>
                    <h3 className="px-4 pt-4 pb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
                        Vehicle Count
                    </h3>
                    <VehicleCount emission={liveEmission} />
                </div>
            </div>
        </div>
    );
}