import type { ActivityGridFeature } from "../types";

export const GRID_LOD_COARSE_BELOW = 13;
export const COARSE_CELL_DEGREES = 0.02;

type Position = [number, number];
type Group = { weight: number; weighted: number; count: number };

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

function firstRing(geometry: ActivityGridFeature["geometry"]): Position[] | null {
    const coordinates = geometry.coordinates;
    if (geometry.type === "Polygon") return (coordinates as Position[][])?.[0] ?? null;
    if (geometry.type === "MultiPolygon") return (coordinates as Position[][][])?.[0]?.[0] ?? null;
    return null;
}

function centroid(geometry: ActivityGridFeature["geometry"]): Position | null {
    const ring = firstRing(geometry);
    if (!ring || ring.length < 3) return null;
    const points = ring.slice(0, -1);
    const usable = points.length ? points : ring;
    const total = usable.reduce<Position>((sum, point) => [sum[0] + point[0], sum[1] + point[1]], [0, 0]);
    return [total[0] / usable.length, total[1] / usable.length];
}

function cellKey(center: Position): string {
    return `${Math.floor(center[0] / COARSE_CELL_DEGREES)}:${Math.floor(center[1] / COARSE_CELL_DEGREES)}`;
}

// Features must already carry the 0-5 render `potential` (set by the caller
// from `klasifikasi_potensi`). Groups adjacent cells into snapped super-cells
// and overwrites each cell's potential with the group's area-weighted mean
// tier. This is a visual approximation, not an independently scored cell:
// `hex_id` is cleared to block panel drill-down and `aggregated_count` records
// how many cells were merged so the UI can label it.
export function aggregateCoarseGrid(features: ActivityGridFeature[]): ActivityGridFeature[] {
    const groups = new Map<string, Group>();
    const keys = features.map((feature) => {
        const center = centroid(feature.geometry);
        if (!center) return null;
        const key = cellKey(center);
        const group = groups.get(key) ?? { weight: 0, weighted: 0, count: 0 };
        group.count += 1;
        const potential = feature.properties.potential ?? 0;
        if (potential >= 1) {
            const weight = Number(feature.properties.luas_km2) || 1;
            group.weight += weight;
            group.weighted += weight * potential;
        }
        groups.set(key, group);
        return key;
    });

    return features.map((feature, index) => {
        const group = keys[index] ? groups.get(keys[index] as string) : undefined;
        const potential = group && group.weight > 0 ? Math.round(group.weighted / group.weight) : 0;
        return {
            ...feature,
            properties: { ...feature.properties, potential, hex_id: null, aggregated_count: group?.count ?? 1 },
        };
    });
}
