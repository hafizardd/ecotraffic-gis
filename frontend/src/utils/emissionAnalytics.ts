import type { AnalyticsQuery, EmissionAnalyticsFilter, RealtimeSegmentEmission } from "../types";

export function analyticsQuery(filter: EmissionAnalyticsFilter, now: string): AnalyticsQuery {
    const to = filter.to ?? now;
    const from = filter.from ?? new Date(Date.parse(to) - parseInt(filter.timeRange) * 3600000).toISOString();
    return { from, to, ...(filter.segmentId ? { segment_id: filter.segmentId } : {}), ...(filter.corridorId ? { corridor_id: filter.corridorId } : {}) };
}

export function isNewerSegment(incoming: Pick<RealtimeSegmentEmission, "observed_at" | "processed_at">, current?: Pick<RealtimeSegmentEmission, "observed_at" | "processed_at">): boolean {
    const observed = Date.parse(incoming.observed_at);
    const processed = Date.parse(incoming.processed_at);
    if (!Number.isFinite(observed) || !Number.isFinite(processed)) return false;
    if (!current) return true;
    const previous = Date.parse(current.observed_at);
    return observed > previous || (observed === previous && processed >= Date.parse(current.processed_at));
}

export function analyticsLiveStatus(observedAt: string | null, staleAfter: number, source: string, now: number): "LIVE" | "STALE" | "HISTORICAL" | "NO DATA" {
    if (!observedAt || !Number.isFinite(Date.parse(observedAt))) return "NO DATA";
    if (source !== "LIVE") return "HISTORICAL";
    return Math.max(0, now - Date.parse(observedAt)) / 1000 <= staleAfter ? "LIVE" : "STALE";
}

export function validRealtimeSegment(value: unknown): value is RealtimeSegmentEmission {
    if (!value || typeof value !== "object") return false;
    const row = value as Partial<RealtimeSegmentEmission>;
    return typeof row.segment_id === "string" && typeof row.corridor_id === "string"
        && typeof row.observed_at === "string" && typeof row.processed_at === "string"
        && !!row.emissions_kg_h && ["tsp", "co", "nox", "so2", "hc", "co2", "ch4", "n2o"].every((key) => {
            const v = (row.emissions_kg_h as Record<string, unknown>)[key];
            return v === null || (typeof v === "number" && Number.isFinite(v));
        });
}
