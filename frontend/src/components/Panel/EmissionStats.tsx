"use client"

import { useEmissionsContext } from "@/context/EmissionsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import Skeleton from "@/components/ui/Skeleton";

interface EmissionStatsProps {
    cameraId: string;
}

export default function EmissionStats({ cameraId }: EmissionStatsProps) {
    const { emissionMap } = useEmissionsContext();
    const liveEmission = emissionMap.get(cameraId) ?? null;
    
    if(!liveEmission) {
        return <div className="stat-grid">{EMISSION_DEFINITIONS.map(({ key }) => (
            <div key={key} className="stat-card"><Skeleton height={10} width="58%" /><Skeleton height={18} width="72%" /></div>
        ))}</div>
    }

    const emissions = liveEmission.source === "tracking" && liveEmission.instant_emission
        ? liveEmission.instant_emission
        : liveEmission;
    
    return (
        <div className="stat-grid">
            {EMISSION_DEFINITIONS.map(({ key, field, label }) => (
                <div key={key} className={`stat-card pollutant-${key}`}>
                    <div className="stat-label"><span className="pollutant-dot" />{label}</div>
                <div className="stat-value">{emissions[field] == null ? "N/A" : Number(emissions[field]).toFixed(2)}<small>g/min</small></div>
                </div>
            ))}
        </div>
    );
}
