"use client"

import { useEmissionsContext } from "@/context/EmissionsContext";

interface EmissionStatsProps {
    cameraId: string;
}

export default function EmissionStats({ cameraId }: EmissionStatsProps) {
    const emissionMap = useEmissionsContext();
    const liveEmission = emissionMap.get(cameraId) ?? null;
    
    if(!liveEmission) {
        return <div className="data-empty"><span className="loading-spinner small" />Menunggu data emisi real-time...</div>
    }
    
    const stats = [
        { label: "CO", value: liveEmission.total_co_g_per_min.toFixed(2), unit: "g/min", tone: "co" },
        { label: "NOx", value: liveEmission.total_nox_g_per_min.toFixed(2), unit: "g/min", tone: "nox" },
        { label: "PM", value: liveEmission.total_pm_g_per_min.toFixed(2), unit: "g/min", tone: "pm" },
        { label: "NMVOC", value: liveEmission.total_nmvoc_g_per_min.toFixed(2), unit: "g/min", tone: "nmvoc" },
    ];

    return (
        <div className="stat-grid">
            {stats.map((stat) => (
                <div key={stat.label} className={`stat-card pollutant-${stat.tone}`}>
                    <div className="stat-label"><span className="pollutant-dot" />{stat.label}</div>
                    <div className="stat-value">{stat.value}<small>{stat.unit}</small></div>
                </div>
            ))}
        </div>
    );
}
