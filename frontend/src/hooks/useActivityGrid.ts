import { useEffect, useRef, useState } from "react";
import { fetchActivityGrid, fetchActivityGridAvailableHours, fetchActivityGridHexHourly } from "@/services/api";
import { ActivityGridFeatureCollection, ActivityGridHourPoint } from "@/types";
import type { GridLod } from "@/utils/activityGrid";

const empty: ActivityGridFeatureCollection = { type: "FeatureCollection", features: [] };

// ponytail: cache is bounded by a blunt clear, not LRU. A session rarely holds
// more than a screenful of bbox/hour/lod combos; add eviction only if the map
// is panned across the whole region for minutes.
const CACHE_LIMIT = 60;
const BBOX_DECIMALS = 4; // ~11 m, so sub-block pans reuse the cached snapshot

function cacheKey(bbox: string | null, hour: string | null, lod: GridLod): string {
    const rounded = bbox ? bbox.split(",").map((v) => Number(v).toFixed(BBOX_DECIMALS)).join(",") : "all";
    return `${lod}|${hour ?? ""}|${rounded}`;
}

// Settles fire once per gesture (see MapView onMoveEnd), so a short debounce is
// enough to coalesce a rapid zoom double-tap. A cache keyed on the rounded
// bbox/hour/lod returns instantly on revisits, and the previous frame stays on
// screen (dimmed via `stale`) until the new one arrives, so zooming never
// blanks the grid. The in-flight request is still aborted on the next change.
export default function useActivityGrid(bbox: string | null, hour: string | null, enabled: boolean, lod: GridLod = "fine") {
    const [activityGrid, setActivityGrid] = useState<ActivityGridFeatureCollection>(empty);
    const [error, setError] = useState<Error | null>(null);
    const [stale, setStale] = useState(false);
    const cache = useRef(new Map<string, ActivityGridFeatureCollection>());

    useEffect(() => {
        if (!enabled) return;
        const key = cacheKey(bbox, hour, lod);
        const cached = cache.current.get(key);
        if (cached) {
            setActivityGrid(cached);
            setStale(false);
            setError(null);
            return;
        }
        const controller = new AbortController();
        const timer = setTimeout(() => {
            setStale(true);
            fetchActivityGrid(bbox ?? undefined, hour, lod, controller.signal)
                .then((value) => {
                    if (cache.current.size >= CACHE_LIMIT) cache.current.clear();
                    cache.current.set(key, value);
                    setActivityGrid(value);
                    setStale(false);
                    setError(null);
                })
                .catch((e) => { if (!controller.signal.aborted) setError(e instanceof Error ? e : new Error(String(e))); });
        }, 120);
        return () => { clearTimeout(timer); controller.abort(); };
    }, [bbox, hour, enabled, lod]);

    return { activityGrid, error, stale };
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

// Per-hex 24h pattern for the detail panel. The caller mounts this per hex, so
// the initial empty state is the loading state; scrubbing hours in the panel
// does not refetch the series.
export function useActivityGridHexHourly(hexId: number): ActivityGridHourPoint[] {
    const [series, setSeries] = useState<ActivityGridHourPoint[]>([]);

    useEffect(() => {
        let mounted = true;
        fetchActivityGridHexHourly(hexId)
            .then((value) => mounted && setSeries(value.series))
            .catch(() => mounted && setSeries([]));
        return () => {
            mounted = false;
        };
    }, [hexId]);

    return series;
}
