"use client"

import { useEmissionsContext } from "@/context/EmissionsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import Skeleton from "@/components/ui/Skeleton";
import { EmissionUpdate } from "@/types";
import { formatNumber } from "@/utils/format";
import { POLLUTANT_DOT_CLASS, POLLUTANT_TEXT_CLASS, STAT_CARD_CLASS, STAT_GRID_CLASS, STAT_LABEL_CLASS, STAT_VALUE_CLASS } from "@/styles/tailwind";

interface EmissionStatsProps {
    cameraId: string;
    // Neighbor estimate override; when absent the camera's own live value wins.
    emission?: EmissionUpdate | null;
}

export default function EmissionStats({ cameraId, emission }: EmissionStatsProps) {
    const { emissionMap } = useEmissionsContext();
    const liveEmission = emission ?? emissionMap.get(cameraId) ?? null;
    
    if(!liveEmission) {
        return <div className={STAT_GRID_CLASS}>{EMISSION_DEFINITIONS.map(({ key }) => (
            <div key={key} className={STAT_CARD_CLASS}><Skeleton height={10} width="58%" /><Skeleton height={18} width="72%" /></div>
        ))}</div>
    }

    const emissions = liveEmission.source === "tracking" && liveEmission.instant_emission
        ? liveEmission.instant_emission
        : liveEmission;
    
    return (
        <div className={STAT_GRID_CLASS}>
            {EMISSION_DEFINITIONS.map(({ key, field, label }) => (
                <div key={key} className={`${STAT_CARD_CLASS} ${POLLUTANT_TEXT_CLASS[key]}`}>
                    <div className={STAT_LABEL_CLASS}><span className={POLLUTANT_DOT_CLASS} />{label}</div>
                <div className={STAT_VALUE_CLASS}>{emissions[field] == null ? "N/A" : formatNumber(Number(emissions[field]))}<small>g/min</small></div>
                </div>
            ))}
        </div>
    );
}
