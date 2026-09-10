export const API_BASE = process.env.NEXT_PUBLIC_API_URL
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL

import { CameraEmissionsResponse, CameraFeatureCollection, EmissionSummary, SegmentEmissionDetail, SegmentFeatureCollection, SpatialFeatureCollection } from "@/types";
import type { AnalyticsQuery, AnalyticsResponse, AnalyticsSegmentOption, EmissionHistoryResponse, EmissionTrendPoint, LatestSegmentEmissionsResponse, PollutantComposition, PollutantKey, TopEmissionCorridor } from "@/types";

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

function analyticsUrl(path: string, query: Partial<AnalyticsQuery> = {}, extra: Record<string, string> = {}) {
    const params = new URLSearchParams(extra);
    for (const [key, value] of Object.entries(query)) if (value) params.set(key, value);
    return `${API_BASE ?? ""}/api/analytics/emissions/${path}?${params}`;
}

async function analyticsFetch<T>(path: string, query: Partial<AnalyticsQuery>, signal?: AbortSignal, extra?: Record<string, string>): Promise<T> {
    const response = await fetch(analyticsUrl(path, query, extra), { signal, cache: "no-store" }).catch((error: Error) => {
        if (signal?.aborted) throw error;
        throw new Error("Tidak dapat menghubungi backend analitik.");
    });
    if (!response.ok) {
        const body: { detail?: unknown } = await response.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : `Gagal memuat analitik (${response.status})`);
    }
    return response.json() as Promise<T>;
}

export const fetchEmissionTrend = (query: AnalyticsQuery, signal?: AbortSignal) =>
    analyticsFetch<AnalyticsResponse<EmissionTrendPoint> & { bucket: string }>("trend", query, signal);
export const fetchTopEmissionCorridors = (query: AnalyticsQuery, pollutant: PollutantKey = "co2", signal?: AbortSignal) =>
    analyticsFetch<AnalyticsResponse<TopEmissionCorridor>>("top-corridors", query, signal, { pollutant, limit: "5" });
export const fetchPollutantComposition = (query: AnalyticsQuery, signal?: AbortSignal) =>
    analyticsFetch<AnalyticsResponse<PollutantComposition> & { sample_count: number }>("composition", query, signal);
export const fetchLatestSegmentEmissions = (query: Partial<AnalyticsQuery> = {}, signal?: AbortSignal) =>
    analyticsFetch<LatestSegmentEmissionsResponse>("latest", query, signal);
export const fetchEmissionHistory = (query: AnalyticsQuery, page = 1, signal?: AbortSignal) =>
    analyticsFetch<EmissionHistoryResponse>("history", query, signal, { page: String(page), page_size: "25" });
export const fetchAnalyticsOptions = (signal?: AbortSignal) =>
    analyticsFetch<{ segments: AnalyticsSegmentOption[] }>("options", {}, signal);

export async function exportEmissionHistory(query: AnalyticsQuery, format: "csv" | "json"): Promise<void> {
    const response = await fetch(analyticsUrl("export", query, { format }), { cache: "no-store" });
    if (!response.ok) {
        const body: { detail?: unknown } = await response.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : `Ekspor gagal (${response.status})`);
    }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url; link.download = `emission-history.${format}`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
