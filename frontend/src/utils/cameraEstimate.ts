import type { CameraFeature, EmissionUpdate, HistoricalCameraEmission } from "@/types";

// A labeled stand-in value derived from the nearest camera that actually has a
// reading. Never presented as this camera's own live data.
export interface NeighborEstimate {
    cameraId: string;
    cameraName: string;
    distanceKm: number;
    emission: EmissionUpdate | null;
    historical: HistoricalCameraEmission | null;
}

const EARTH_RADIUS_KM = 6371;

export function haversineKm(a: [number, number], b: [number, number]): number {
    const toRad = (deg: number) => (deg * Math.PI) / 180;
    const dLat = toRad(b[1] - a[1]);
    const dLon = toRad(b[0] - a[0]);
    const h = Math.sin(dLat / 2) ** 2
        + Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLon / 2) ** 2;
    return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(h)));
}

// Nearest-neighbor fallback for a CCTV point with no value of its own. Returns
// null when no other camera has data, so callers can show a real empty state
// rather than fabricate a number.
export function neighborEstimate(
    target: CameraFeature,
    cameras: CameraFeature[],
    emissionMap: Map<string, EmissionUpdate>,
    historicalMap: Map<string, HistoricalCameraEmission>,
): NeighborEstimate | null {
    const origin = target.geometry.coordinates;
    let best: NeighborEstimate | null = null;
    for (const candidate of cameras) {
        const id = candidate.properties.camera_id;
        if (id === target.properties.camera_id) continue;
        const emission = emissionMap.get(id) ?? null;
        const historical = historicalMap.get(id) ?? null;
        if (!emission && !historical) continue;
        const distanceKm = haversineKm(origin, candidate.geometry.coordinates);
        if (!best || distanceKm < best.distanceKm) {
            best = { cameraId: id, cameraName: candidate.properties.name || id, distanceKm, emission, historical };
        }
    }
    return best;
}
