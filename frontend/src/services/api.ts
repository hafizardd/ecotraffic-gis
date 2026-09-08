export const API_BASE = process.env.NEXT_PUBLIC_API_URL
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL

import { CameraEmissionsResponse, CameraFeatureCollection, EmissionSummary, SegmentEmissionDetail, SegmentFeatureCollection, SpatialFeatureCollection } from "@/types";

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

export async function fetchEmissionsSummary(): Promise<EmissionSummary> {
    const response = await fetch(`${API_BASE}/api/emissions/summary`);
    if (!response.ok) throw new Error(`Failed to fetch emission summary: ${response.statusText}`);
    return response.json();
}

export interface SegmentHistoryBucket {
    bucket_start: string;
    segment_id: string;
    avg_total_emission_g_h: number;
    avg_volume_per_hour: number;
    decision_score: number | null;
    priority: string | null;
    sample_count: number;
}

export async function fetchSegmentEmissionHistory(segmentId?: string): Promise<SegmentHistoryBucket[]> {
    const params = new URLSearchParams({ bucket: "hour" });
    if (segmentId) params.set("segment_id", segmentId);
    const response = await fetch(`${API_BASE}/api/emissions/segments/history?${params}`);
    if (!response.ok) throw new Error(`Failed to fetch segment history: ${response.statusText}`);
    return response.json();
}

async function fetchSpatial(path: string): Promise<SpatialFeatureCollection> {
    const response = await fetch(`${API_BASE}${path}`);
    if (!response.ok) throw new Error(`Failed to fetch spatial layer: ${response.statusText}`);
    return response.json();
}

export const fetchPopulationZones = () => fetchSpatial("/api/spatial/population-zones");
export const fetchSurveyStops = (bbox?: string) => fetchSpatial(`/api/spatial/survey-stops?limit=200${bbox ? `&bbox=${encodeURIComponent(bbox)}` : ""}`);
