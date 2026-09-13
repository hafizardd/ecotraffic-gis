import { useEffect, useMemo, useRef, useState } from "react";
import { fetchActivityGrid, fetchActivityGridAvailableHours } from "@/services/api";
import { ActivityGridFeatureCollection } from "@/types";
import { hourKey, isWholeRegionLod, type GridLod } from "@/utils/activityGrid";

const empty: ActivityGridFeatureCollection = { type: "FeatureCollection", features: [] };

// ponytail: cache is bounded by a blunt clear, not LRU. A session rarely holds
// more than a screenful of bbox/hour/lod combos; add eviction only if the map
// is panned across the whole region for minutes.
const CACHE_LIMIT = 60;
const BBOX_DECIMALS = 4; // ~11 m, so sub-block pans reuse the cached snapshot
const LIVE_POLL_MS = 5000; // newest facts land on the ~60s reconcile cadence

function cacheKey(bbox: string | null, hour: string | null, lod: GridLod, live: boolean): string {
    const rounded = bbox ? bbox.split(",").map((v) => Number(v).toFixed(BBOX_DECIMALS)).join(",") : "all";
    // Keyed by hour-of-day: the static profile is the same for any calendar day.
    // Live ignores the hour entirely (newest observed facts, no time filter).
    return live ? `live|${lod}|${rounded}` : `${lod}|${hourKey(hour)}|${rounded}`;
}

// Settles fire once per gesture (see MapView onMoveEnd), so a short debounce is
// enough to coalesce a rapid zoom double-tap. A cache keyed on the rounded
// bbox/hour/lod returns instantly on revisits, and the previous frame stays on
// screen (dimmed via `stale`) until the new one arrives, so zooming never
// blanks the grid. The in-flight request is still aborted on the next change.
// In live mode the cache is bypassed and the fetch repolls until mode or
// viewport changes, so the two tracking cameras' hexes track their newest facts.
export default function useActivityGrid(bbox: string | null, hour: string | null, enabled: boolean,
                                        lod: GridLod = "fine", hours: string[] = [],
                                        prefetchTier: GridLod | null = null, live = false) {
    const [activityGrid, setActivityGrid] = useState<ActivityGridFeatureCollection>(empty);
    const [error, setError] = useState<Error | null>(null);
    const [stale, setStale] = useState(false);
    const [updatedAt, setUpdatedAt] = useState<string | null>(null);
    const [liveTick, setLiveTick] = useState(0);
    const cache = useRef(new Map<string, ActivityGridFeatureCollection>());
    // Aggregated tiers are region-wide, so they ignore the viewport and stay
    // cached across pans (only `fine` keeps a viewport-scoped key).
    const scopeBbox = useMemo(() => (isWholeRegionLod(lod) ? null : bbox), [lod, bbox]);

    // Live repoll. The reconcile cadence is ~minute-scale, so this is a prompt
    // pick-up of the newest facts, not a high-frequency feed.
    useEffect(() => {
        if (!enabled || !live) return;
        const id = window.setInterval(() => setLiveTick((tick) => tick + 1), LIVE_POLL_MS);
        return () => window.clearInterval(id);
    }, [enabled, live]);

    useEffect(() => {
        if (!enabled) return;
        const key = cacheKey(scopeBbox, hour, lod, live);
        const cached = cache.current.get(key);
        // Live never serves the cache: every poll re-reads the newest facts.
        if (!live && cached) {
            setActivityGrid(cached);
            setStale(false);
            setError(null);
            return;
        }
        const controller = new AbortController();
        const timer = setTimeout(() => {
            setStale(true);
            fetchActivityGrid(scopeBbox ?? undefined, live ? null : hour, lod, controller.signal, live ? "live" : "replay")
                .then((value) => {
                    if (cache.current.size >= CACHE_LIMIT) cache.current.clear();
                    cache.current.set(key, value);
                    setActivityGrid(value);
                    setStale(false);
                    setError(null);
                    setUpdatedAt(new Date().toISOString());
                })
                .catch((e) => { if (!controller.signal.aborted) setError(e instanceof Error ? e : new Error(String(e))); });
        }, live ? 0 : 120);
        return () => { clearTimeout(timer); controller.abort(); };
    }, [scopeBbox, hour, enabled, lod, live, liveTick]);

    // Prefetch the whole 24h profile for the current viewport once, so scrubbing
    // the slider is a cache hit (instant, no per-tick network round-trip). The
    // profile is meaningless in live mode, so skip it there.
    useEffect(() => {
        if (!enabled || live || hours.length === 0) return;
        const controller = new AbortController();
        let cancelled = false;
        (async () => {
            for (const candidate of hours) {
                if (cancelled) return;
                const key = cacheKey(scopeBbox, candidate, lod, false);
                if (cache.current.has(key)) continue;
                try {
                    const value = await fetchActivityGrid(scopeBbox ?? undefined, candidate, lod, controller.signal, "replay");
                    if (cancelled) return;
                    if (cache.current.size >= CACHE_LIMIT) cache.current.clear();
                    cache.current.set(key, value);
                } catch {
                    return;
                }
            }
        })();
        return () => { cancelled = true; controller.abort(); };
    }, [scopeBbox, enabled, lod, hours, live]);

    // Near a tier boundary, warm the adjacent tier for the current hour so a
    // mid-zoom size swap is a cache hit instead of a wait.
    useEffect(() => {
        if (!enabled || live || !prefetchTier || prefetchTier === lod || !hour) return;
        const targetScope = isWholeRegionLod(prefetchTier) ? null : bbox;
        const key = cacheKey(targetScope, hour, prefetchTier, false);
        if (cache.current.has(key)) return;
        const controller = new AbortController();
        fetchActivityGrid(targetScope ?? undefined, hour, prefetchTier, controller.signal, "replay")
            .then((value) => {
                if (controller.signal.aborted) return;
                if (cache.current.size >= CACHE_LIMIT) cache.current.clear();
                cache.current.set(key, value);
            })
            .catch(() => {});
        return () => controller.abort();
    }, [prefetchTier, lod, bbox, hour, enabled, live]);

    return { activityGrid, error, stale, updatedAt };
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
