export const GRID_LOD_COARSE_BELOW = 13;

export function gridLod(zoom: number): "coarse" | "native" {
    return zoom < GRID_LOD_COARSE_BELOW ? "coarse" : "native";
}

// Slider position within the available hours; -1 when there is nothing to
// scrub, otherwise clamp to [earliest, latest] (latest is the fallback).
export function sliderIndex(hours: string[], value: string | null): number {
    if (hours.length === 0) return -1;
    if (!value) return hours.length - 1;
    const index = hours.indexOf(value);
    return index === -1 ? hours.length - 1 : index;
}
