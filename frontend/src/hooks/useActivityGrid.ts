import { useEffect, useMemo, useRef, useState } from "react";
import { fetchActivityGrid, fetchActivityGridAvailableHours, fetchActivityGridHexHourly } from "@/services/api";
import { ActivityGridFeatureCollection, ActivityGridHourPoint } from "@/types";
import { hourKey, isWholeRegionLod, type GridLod } from "@/utils/activityGrid";

const empty: ActivityGridFeatureCollection = { type: "FeatureCollection", features: [] };

// ponytail: cache is bounded by a blunt clear, not LRU. A session rarely holds
// more than a screenful of bbox/hour/lod combos; add eviction only if the map
// is panned across the whole region for minutes.
const CACHE_LIMIT = 60;
const BBOX_DECIMALS = 4; // ~11 m, so sub-block pans reuse the cached snapshot

function cacheKey(bbox: string | null, hour: string | null, lod: GridLod): string {
    const rounded = bbox ? bbox.split(",").map((v) => Number(v).toFixed(BBOX_DECIMALS)).join(",") : "all";
    // Keyed by hour-of-day: the static profile is the same for any calendar day.
    return `${lod}|${hourKey(hour)}|${rounded}`;
}

// Settles fire once per gesture (see MapView onMoveEnd), so a short debounce is
// enough to coalesce a rapid zoom double-tap. A cache keyed on the rounded
// bbox/hour/lod returns instantly on revisits, and the previous frame stays on
// screen (dimmed via `stale`) until the new one arrives, so zooming never
// blanks the grid. The in-flight request is still aborted on the next change.
export default function useActivityGrid(bbox: string | null, hour: string | null, enabled: boolean,
                                        lod: GridLod = "fine", hours: string[] = [], prefetchTier: GridLod | null = null) {
    const [activityGrid, setActivityGrid] = useState<ActivityGridFeatureCollection>(empty);
    const [error, setError] = useState<Error | null>(null);
    const [stale, setStale] = useState(false);
    const cache = useRef(new Map<string, ActivityGridFeatureCollection>());
    // Aggregated tiers are region-wide, so they ignore the viewport and stay
    // cached across pans (only `fine` keeps a viewport-scoped key).
    const scopeBbox = useMemo(() => (isWholeRegionLod(lod) ? null : bbox), [lod, bbox]);

    useEffect(() => {
        if (!enabled) return;
        const key = cacheKey(scopeBbox, hour, lod);
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
            fetchActivityGrid(scopeBbox ?? undefined, hour, lod, controller.signal)
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
    }, [scopeBbox, hour, enabled, lod]);

    // Prefetch the whole 24h profile for the current viewport once, so scrubbing
    // the slider is a cache hit (instant, no per-tick network round-trip).
    useEffect(() => {
        if (!enabled || hours.length === 0) return;
        const controller = new AbortController();
        let cancelled = false;
        (async () => {
            for (const candidate of hours) {
                if (cancelled) return;
                const key = cacheKey(scopeBbox, candidate, lod);
                if (cache.current.has(key)) continue;
                try {
                    const value = await fetchActivityGrid(scopeBbox ?? undefined, candidate, lod, controller.signal);
                    if (cancelled) return;
                    if (cache.current.size >= CACHE_LIMIT) cache.current.clear();
                    cache.current.set(key, value);
                } catch {
                    return;
                }
            }
        })();
        return () => { cancelled = true; controller.abort(); };
    }, [scopeBbox, enabled, lod, hours]);

    // Near a tier boundary, warm the adjacent tier for the current hour so a
    // mid-zoom size swap is a cache hit instead of a wait.
    useEffect(() => {
        if (!enabled || !prefetchTier || prefetchTier === lod || !hour) return;
        const targetScope = isWholeRegionLod(prefetchTier) ? null : bbox;
        const key = cacheKey(targetScope, hour, prefetchTier);
        if (cache.current.has(key)) return;
        const controller = new AbortController();
        fetchActivityGrid(targetScope ?? undefined, hour, prefetchTier, controller.signal)
            .then((value) => {
                if (controller.signal.aborted) return;
                if (cache.current.size >= CACHE_LIMIT) cache.current.clear();
                cache.current.set(key, value);
            })
            .catch(() => {});
        return () => controller.abort();
    }, [prefetchTier, lod, bbox, hour, enabled]);

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
