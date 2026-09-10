import { useEffect, useState } from "react";
import { fetchActivityGrid } from "@/services/api";
import { ActivityGridFeatureCollection } from "@/types";

const empty: ActivityGridFeatureCollection = { type: "FeatureCollection", features: [] };

export default function useActivityGrid(bbox: string | null, enabled: boolean) {
    const [activityGrid, setActivityGrid] = useState<ActivityGridFeatureCollection>(empty);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (enabled) {
                fetchActivityGrid(bbox ?? undefined)
                    .then(setActivityGrid)
                    .catch((e) => setError(e instanceof Error ? e : new Error(String(e))));
            }
        }, 250);
        return () => clearTimeout(timer);
    }, [bbox, enabled]);

    return { activityGrid, error };
}
