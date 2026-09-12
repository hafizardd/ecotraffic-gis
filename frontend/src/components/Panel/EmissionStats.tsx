"use client"

import { useEmissionsContext } from "@/context/EmissionsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import Skeleton from "@/components/ui/Skeleton";
import { EmissionUpdate } from "@/types";
import { formatNumber } from "@/utils/format";

interface EmissionStatsProps {
    cameraId: string;
    // Neighbor estimate override; when absent the camera's own live value wins.
    emission?: EmissionUpdate | null;
}

export default function EmissionStats({ cameraId, emission }: EmissionStatsProps) {
    const { emissionMap } = useEmissionsContext();
    const liveEmission = emission ?? emissionMap.get(cameraId) ?? null;
    
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
                <div className="stat-value">{emissions[field] == null ? "N/A" : formatNumber(Number(emissions[field]))}<small>g/min</small></div>
                </div>
            ))}
        </div>
    );
}
