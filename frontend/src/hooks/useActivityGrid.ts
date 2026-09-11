import { useEffect, useState } from "react";
import { fetchActivityGrid, fetchActivityGridAvailableHours } from "@/services/api";
import { ActivityGridFeatureCollection } from "@/types";

const empty: ActivityGridFeatureCollection = { type: "FeatureCollection", features: [] };

export default function useActivityGrid(bbox: string | null, hour: string | null, enabled: boolean) {
    const [activityGrid, setActivityGrid] = useState<ActivityGridFeatureCollection>(empty);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (enabled) {
                fetchActivityGrid(bbox ?? undefined, hour)
                    .then(setActivityGrid)
                    .catch((e) => setError(e instanceof Error ? e : new Error(String(e))));
            }
        }, 250);
        return () => clearTimeout(timer);
    }, [bbox, hour, enabled]);

    return { activityGrid, error };
}

// Availability is fetched once so the slider never probes hour-by-hour.
export function useActivityGridHours(enabled: boolean): string[] {
    const [hours, setHours] = useState<string[]>([]);

    useEffect(() => {
        if (!enabled) return;
        let mounted = true;
        fetchActivityGridAvailableHours()
            .then((value) => mounted && setHours(value.hours))
            .catch(() => mounted && setHours([]));
        return () => {
            mounted = false;
        };
    }, [enabled]);

    return hours;
}
