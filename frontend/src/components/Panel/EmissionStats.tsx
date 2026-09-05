"use client"

import { useEmissionsContext } from "@/context/EmissionsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";

interface EmissionStatsProps {
    cameraId: string;
}

export default function EmissionStats({ cameraId }: EmissionStatsProps) {
    const { emissionMap } = useEmissionsContext();
    const liveEmission = emissionMap.get(cameraId) ?? null;
    
    if(!liveEmission) {
        return <div className="data-empty"><span className="loading-spinner small" />Menunggu data emisi real-time...</div>
    }
    
    return (
        <div className="stat-grid">
            {EMISSION_DEFINITIONS.map(({ key, field, label }) => (
                <div key={key} className={`stat-card pollutant-${key}`}>
                    <div className="stat-label"><span className="pollutant-dot" />{label}</div>
                    <div className="stat-value">{Number(liveEmission[field] ?? 0).toFixed(2)}<small>g/min</small></div>
                </div>
            ))}
        </div>
    );
}
