import { useEffect, useState } from "react";
import { fetchActivityGrid, fetchActivityGridAvailableHours } from "@/services/api";
import { ActivityGridFeatureCollection } from "@/types";

const empty: ActivityGridFeatureCollection = { type: "FeatureCollection", features: [] };

// bbox pans settle at 250ms; the hour slider is a more continuous gesture so it
// uses a tighter 130ms debounce. Either way the in-flight request is aborted on
// the next change so a slow earlier hour can never overwrite a later one.
export default function useActivityGrid(bbox: string | null, hour: string | null, enabled: boolean, lod: "coarse" | "native" = "native") {
    const [activityGrid, setActivityGrid] = useState<ActivityGridFeatureCollection>(empty);
    const [error, setError] = useState<Error | null>(null);
    const [debouncedBbox, setDebouncedBbox] = useState(bbox);

    useEffect(() => {
        if (bbox === debouncedBbox) return;
        const timer = setTimeout(() => setDebouncedBbox(bbox), 250);
        return () => clearTimeout(timer);
    }, [bbox, debouncedBbox]);

    useEffect(() => {
        if (!enabled) return;
        const controller = new AbortController();
        const timer = setTimeout(() => {
            fetchActivityGrid(debouncedBbox ?? undefined, hour, lod, controller.signal)
                .then((value) => { setActivityGrid(value); setError(null); })
                .catch((e) => { if (!controller.signal.aborted) setError(e instanceof Error ? e : new Error(String(e))); });
        }, 130);
        return () => { clearTimeout(timer); controller.abort(); };
    }, [debouncedBbox, hour, enabled, lod]);

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
