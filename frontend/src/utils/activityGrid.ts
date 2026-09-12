// Four-tier, zoom-driven H3 resolution ladder. `fine` is the true native
// per-hex set; the coarser tiers roll native cells up into H3 super-cells at
// res 8 / 7 / 6, remapped per request by the backend.
export type GridLod = "coarse" | "medium" | "sub" | "fine";

// Fine covers the normal street-level view, so zooming in always reveals the
// full per-cell grid; the coarser tiers only kick in once genuinely zoomed out.
export const GRID_LOD_COARSE_BELOW = 10;
export const GRID_LOD_MEDIUM_BELOW = 12;
export const GRID_LOD_SUB_BELOW = 14;

export const GRID_LOD_RESOLUTION: Record<GridLod, string> = {
    coarse: "H3-6",
    medium: "H3-7",
    sub: "H3-8",
    fine: "native ±100 m",
};

export function gridLod(zoom: number): GridLod {
    if (zoom < GRID_LOD_COARSE_BELOW) return "coarse";
    if (zoom < GRID_LOD_MEDIUM_BELOW) return "medium";
    if (zoom < GRID_LOD_SUB_BELOW) return "sub";
    return "fine";
}

// Ladder order + each tier's lower boundary. `nextGridLod` keeps the current
// tier until the zoom clears a boundary by HYSTERESIS, so resting right on
// 10/12/14 does not thrash between two resolutions (and two fetches). A jump of
// more than one tier (programmatic easeTo, double-click zoom) still lands
// exactly on the target instead of walking the ladder one step per frame.
const LOD_ORDER: readonly GridLod[] = ["coarse", "medium", "sub", "fine"];
const LOD_LOWER_BOUND: Record<GridLod, number> = {
    coarse: Number.NEGATIVE_INFINITY,
    medium: GRID_LOD_COARSE_BELOW,
    sub: GRID_LOD_MEDIUM_BELOW,
    fine: GRID_LOD_SUB_BELOW,
};
const LOD_HYSTERESIS = 0.5;

export function nextGridLod(zoom: number, current: GridLod): GridLod {
    const target = gridLod(zoom);
    const currentIndex = LOD_ORDER.indexOf(current);
    const targetIndex = LOD_ORDER.indexOf(target);
    if (Math.abs(targetIndex - currentIndex) > 1) return target;
    if (targetIndex > currentIndex && zoom < LOD_LOWER_BOUND[target] + LOD_HYSTERESIS) return current;
    if (targetIndex < currentIndex && zoom >= LOD_LOWER_BOUND[current] - LOD_HYSTERESIS) return current;
    return target;
}

// Slider position within the available hours; -1 when there is nothing to
// scrub, otherwise clamp to [earliest, latest] (latest is the fallback).
export function sliderIndex(hours: string[], value: string | null): number {
    if (hours.length === 0) return -1;
    if (!value) return hours.length - 1;
    const index = hours.indexOf(value);
    return index === -1 ? hours.length - 1 : index;
}

// The 24h dataset is one static profile, so any calendar day reuses the same
// buckets: rewrite only the date part of a canonical hour for display/requests.
export function withDay(iso: string, day: string | null): string {
    if (!day) return iso;
    const [year, month, date] = day.split("-").map(Number);
    const moment = new Date(iso);
    moment.setUTCFullYear(year, month - 1, date);
    return moment.toISOString();
}

// Cache key for a profile hour: identical regardless of calendar day, so a day
// switch reuses the already-cached 24h set instead of refetching.
export function hourKey(hour: string | null): string {
    return hour ? hour.slice(11, 16) : "";
}

// Every aggregated LOD is served region-wide so zooming out never reveals empty
// edges; only the native `fine` tier stays viewport-scoped. The count card
// filters features back to the viewport so its label stays truthful.
export function isWholeRegionLod(lod: GridLod): boolean {
    return lod !== "fine";
}

// Adjacent tier to warm up while the user approaches a tier boundary, so the
// size swap during zoom is a cache hit. Pure so it is unit-testable.
const TIER_STEPS: ReadonlyArray<{ boundary: number; coarse: GridLod; fine: GridLod }> = [
    { boundary: GRID_LOD_COARSE_BELOW, coarse: "coarse", fine: "medium" },
    { boundary: GRID_LOD_MEDIUM_BELOW, coarse: "medium", fine: "sub" },
    { boundary: GRID_LOD_SUB_BELOW, coarse: "sub", fine: "fine" },
];
export const TIER_PREFETCH_MARGIN = 0.7;

export function adjacentTierToPrefetch(zoom: number, current: GridLod): GridLod | null {
    for (const { boundary, coarse, fine } of TIER_STEPS) {
        if (Math.abs(zoom - boundary) > TIER_PREFETCH_MARGIN) continue;
        if (current === coarse) return fine;
        if (current === fine) return coarse;
        return null;
    }
    return null;
}

// Cheap viewport test for the count card when features arrive region-wide.
export function featureInBbox(feature: { geometry: { coordinates: unknown } }, bbox: string | null): boolean {
    if (!bbox) return true;
    const [west, south, east, north] = bbox.split(",").map(Number);
    const points: number[][] = [];
    const collect = (value: unknown) => {
        if (!Array.isArray(value)) return;
        if (typeof value[0] === "number" && typeof value[1] === "number") {
            points.push(value as number[]);
        } else {
            for (const item of value) collect(item);
        }
    };
    collect(feature.geometry.coordinates);
    return points.some(([lon, lat]) => lon >= west && lon <= east && lat >= south && lat <= north);
}

export function dataStatusLabel(status: string | null | undefined): string {
    switch (status) {
        case "live": return "Terukur";
        case "fallback": return "Perkiraan sel terdekat";
        case "static": return "Model statis";
        default: return "Tidak tersedia";
    }
}

const NO_DATA_REASONS: Record<string, string> = {
    no_mapped_segment: "Tidak ada segmen jalan yang memotong sel ini.",
    mapped_but_no_volume: "Ada segmen jalan, tetapi tidak ada sampel volume pada jam ini.",
};

export function noDataReasonLabel(reason: string | null | undefined): string | null {
    if (!reason) return null;
    return NO_DATA_REASONS[reason] ?? "Alasan tidak dicatat.";
}
