"use client"

import { useEmissionsContext } from "@/context/EmissionsContext";

interface EmissionStatsProps {
    cameraId: string;
}

export default function EmissionStats({ cameraId }: EmissionStatsProps) {
    const emissionMap = useEmissionsContext();
    const liveEmission = emissionMap.get(cameraId) ?? null;
    
    if(!liveEmission) {
        return <div className="p-4 text-zinc-400 text-sm">Waiting for live data...</div>
    }
    
    const stats = [
        { label: "CO", value: liveEmission.total_co_g_per_min.toFixed(2), unit: "g/min" },
        { label: "NOx", value: liveEmission.total_nox_g_per_min.toFixed(2), unit: "g/min" },
        { label: "PM", value: liveEmission.total_pm_g_per_min.toFixed(2), unit: "g/min" },
        { label: "NMVOC", value: liveEmission.total_nmvoc_g_per_min.toFixed(2), unit: "g/min" },
    ];

    return (
        <div className="grid grid-cols-2 gap-3 p-4">
            {stats.map((stat) => (
                <div
                    key={stat.label}
                    className="bg-zinc-100 dark:bg-zinc-800 rounded-lg p-3"
                >
                    <div className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
                        {stat.label}
                    </div>
                    <div className="text-lg font-semibold mt-1">
                        {stat.value}
                    </div>
                    <div className="text-xs text-zinc-400">{stat.unit}</div>
                </div>
            ))}
        </div>
    );
}