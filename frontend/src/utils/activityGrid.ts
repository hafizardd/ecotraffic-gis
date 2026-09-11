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
