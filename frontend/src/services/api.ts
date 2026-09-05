export const API_BASE = process.env.NEXT_PUBLIC_API_URL
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL

import { CameraEmissionsResponse, CameraFeatureCollection, SegmentEmissionDetail, SegmentFeatureCollection, EmissionUpdate } from "@/types";

export async function fetchCameras(dataSource?: "LIVE" | "HISTORICAL"): Promise<CameraFeatureCollection> {
    const response = await fetch(`${API_BASE}/api/cameras${dataSource ? `?data_source=${dataSource}` : ""}`)

    if(!response.ok) {
        throw new Error(`Failed to fetch cameras: ${response.statusText}`)
    }

    return response.json();
}

export async function fetchSegmentsGeoJSON(): Promise<SegmentFeatureCollection> {
    const response = await fetch(`${API_BASE}/api/segments/geojson`);
    if (!response.ok) throw new Error(`Failed to fetch segments: ${response.statusText}`);
    return response.json();
}

export async function fetchSegmentEmission(segmentId: string): Promise<SegmentEmissionDetail> {
    const response = await fetch(`${API_BASE}/api/emissions/${encodeURIComponent(segmentId)}`);
    if (!response.ok) throw new Error(`Failed to fetch segment emission: ${response.statusText}`);
    return response.json();
}

export async function fetchCameraEmissions(
    camera_id: string,
    limit: number = 1
): Promise<CameraEmissionsResponse> {
    const response = await fetch(`${API_BASE}/api/cameras/${camera_id}/emissions?limit=${limit}`);

    if (!response.ok) throw new Error('Failed to fetch emissions');
    
    return response.json();
}

export async function fetchLatestEmissions(): Promise<EmissionUpdate[]> {
    const response = await fetch(`${API_BASE}/api/emissions/summary`);
    if (!response.ok) throw new Error(`Failed to fetch emission summary: ${response.statusText}`);
    return [];
}
