export const API_BASE = process.env.NEXT_PUBLIC_API_URL
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL

import { ActivityGridFeature, ActivityGridFeatureCollection, ActivityGridHourSeries, BangJoReply, BusStopDetail, CameraEmissionsResponse, CameraFeatureCollection, EmissionSummary, SegmentEmissionDetail, SegmentFeatureCollection, SpatialFeatureCollection } from "@/types";
import type { GridLod } from "@/utils/activityGrid";
import type { AnalyticsQuery, AnalyticsResponse, AnalyticsSegmentOption, EmissionHistoryDeleteResponse, EmissionHistoryResponse, EmissionTrendPoint, LatestSegmentEmissionsResponse, PollutantComposition, PollutantKey, TopEmissionCorridor, VehicleAnalyticsResponse } from "@/types";

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

export const fetchSurveyStops = (bbox?: string) => fetchSpatial(`/api/spatial/survey-stops?limit=200${bbox ? `&bbox=${encodeURIComponent(bbox)}` : ""}`);

export async function fetchActivityGrid(bbox?: string, hour?: string | null, lod: GridLod = "fine", signal?: AbortSignal): Promise<ActivityGridFeatureCollection> {
    const params = new URLSearchParams();
    // Every LOD is viewport-scoped: the count card and quantile breaks are
    // recalculated from whatever is on screen.
    if (bbox) params.set("bbox", bbox);
    if (hour) params.set("hour", hour);
    if (lod !== "fine") params.set("lod", lod);
    const query = params.toString();
    const response = await fetch(`${API_BASE}/api/spatial/activity-grid${query ? `?${query}` : ""}`, { signal });
    if (!response.ok) throw new Error(`Failed to fetch activity grid: ${response.statusText}`);
    return response.json();
}

export interface ActivityGridAvailableHours {
    hours: string[];
    earliest: string | null;
    latest: string | null;
}

export async function fetchActivityGridAvailableHours(): Promise<ActivityGridAvailableHours> {
    const response = await fetch(`${API_BASE}/api/spatial/activity-grid/available-hours`);
    if (!response.ok) throw new Error(`Failed to fetch activity grid hours: ${response.statusText}`);
    return response.json();
}

export async function fetchActivityGridHex(hexId: number, hour?: string | null): Promise<ActivityGridFeature> {
    const response = await fetch(`${API_BASE}/api/spatial/activity-grid/${hexId}${hour ? `?hour=${encodeURIComponent(hour)}` : ""}`);
    if (!response.ok) throw new Error(`Failed to fetch activity grid hex: ${response.statusText}`);
    return response.json();
}

export async function fetchActivityGridHexHourly(hexId: number): Promise<ActivityGridHourSeries> {
    const response = await fetch(`${API_BASE}/api/spatial/activity-grid/${hexId}/hourly`);
    if (!response.ok) throw new Error(`Failed to fetch activity grid hourly series: ${response.statusText}`);
    return response.json();
}

// null = segment is outside the imported grid coverage (normal empty state).
export async function fetchSegmentActivityGrid(segmentId: string): Promise<ActivityGridFeature | null> {
    const response = await fetch(`${API_BASE}/api/spatial/segments/${encodeURIComponent(segmentId)}/activity-grid`);
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Failed to fetch segment activity grid: ${response.statusText}`);
    return response.json();
}

export async function fetchBusStopDetail(sourceId: string): Promise<BusStopDetail> {
    const response = await fetch(`${API_BASE}/api/spatial/survey-stops/${encodeURIComponent(sourceId)}`);
    if (!response.ok) throw new Error(`Failed to fetch bus stop: ${response.statusText}`);
    return response.json();
}

export async function fetchBangJoReply(
    message: string,
    roadSegmentId: string | null,
    history: { role: string; content: string }[],
): Promise<BangJoReply> {
    const response = await fetch(`${API_BASE}/api/chat/bangjo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, road_segment_id: roadSegmentId, history }),
    });
    if (!response.ok) throw new Error(`Bang Jo tidak dapat dihubungi (${response.status})`);
    return response.json();
}

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
export interface EmissionHistoryOptions {
    page?: number; pageSize?: number; sort?: string; order?: "asc" | "desc"; signal?: AbortSignal;
}
export const fetchEmissionHistory = (query: AnalyticsQuery, options: EmissionHistoryOptions = {}) => {
    const { page = 1, pageSize = 25, sort = "period_start", order = "desc", signal } = options;
    return analyticsFetch<EmissionHistoryResponse>("history", query, signal,
        { page: String(page), page_size: String(pageSize), sort, order });
};

export interface DeleteEmissionHistoryOptions {
    page?: number; page_size?: number; sort?: string; order?: "asc" | "desc";
    scope?: "beyond" | "page"; dry_run?: boolean;
}

export async function deleteEmissionHistory(
    query: AnalyticsQuery, options: DeleteEmissionHistoryOptions = {},
): Promise<EmissionHistoryDeleteResponse> {
    const { page = 1, page_size = 25, sort = "period_start", order = "desc", scope = "beyond", dry_run = false } = options;
    const params = new URLSearchParams({
        page: String(page), page_size: String(page_size), sort, order, scope, dry_run: String(dry_run),
    });
    for (const [key, value] of Object.entries(query)) if (value) params.set(key, value);
    const response = await fetch(`${API_BASE ?? ""}/api/analytics/emissions/history?${params}`, { method: "DELETE", cache: "no-store" });
    if (!response.ok) {
        const body: { detail?: unknown } = await response.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : `Gagal menghapus riwayat (${response.status})`);
    }
    return response.json();
}
export const fetchAnalyticsOptions = (signal?: AbortSignal) =>
    analyticsFetch<{ segments: AnalyticsSegmentOption[] }>("options", {}, signal);
export const fetchVehicleAnalytics = (query: AnalyticsQuery, signal?: AbortSignal) =>
    analyticsFetch<VehicleAnalyticsResponse>("vehicles", query, signal);

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
