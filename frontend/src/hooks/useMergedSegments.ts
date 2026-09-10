"use client";

import { useMemo } from "react";
import useSegments from "@/hooks/useSegments";
import { useEmissionsContext } from "@/context/EmissionsContext";
import { SegmentFeature } from "@/types";

export default function useMergedSegments() {
    const { segments, loading, error } = useSegments();
    const { segmentMap } = useEmissionsContext();
    const merged = useMemo<SegmentFeature[]>(
        () =>
            segments.map((segment) => {
                const update = segmentMap.get(segment.properties.segment_id);
                const pollutantTotals = update?.pollutant_totals ?? segment.properties.pollutant_totals;
                const calculatedTotal = pollutantTotals
                    ? Object.values(pollutantTotals).reduce((sum, value) => sum + Number(value), 0)
                    : null;
                return {
                    ...segment,
                    properties: {
                        ...segment.properties,
                        ...(update as Partial<typeof segment.properties>),
                        total_emission_g_h:
                            update?.total_emission_g_h ?? segment.properties.total_emission_g_h ?? calculatedTotal,
                    },
                };
            }),
        [segments, segmentMap],
    );
    return { segments: merged, loading, error };
}
