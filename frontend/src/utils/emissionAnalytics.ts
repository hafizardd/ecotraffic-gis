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

export function pageWindow(current: number, total: number): (number | "gap")[] {
    if (total <= 7) return Array.from({ length: Math.max(total, 1) }, (_, index) => index + 1);
    const pages = [...new Set([1, total, current - 2, current - 1, current, current + 1, current + 2]
        .filter((page) => page >= 1 && page <= total))].sort((a, b) => a - b);
    const window: (number | "gap")[] = [];
    let previous = 0;
    for (const page of pages) {
        if (page - previous > 1) window.push("gap");
        window.push(page);
        previous = page;
    }
    return window;
}

export function numberDuplicateNames(names: string[]): string[] {
    const totals = new Map<string, number>();
    for (const name of names) totals.set(name, (totals.get(name) ?? 0) + 1);
    const seen = new Map<string, number>();
    return names.map((name) => {
        if ((totals.get(name) ?? 0) <= 1) return name;
        const index = (seen.get(name) ?? 0) + 1;
        seen.set(name, index);
        return `${name} ${index}`;
    });
}

export function filterSelectOptions<T extends { label: string }>(options: T[], query: string): T[] {
    const needle = query.trim().toLowerCase();
    if (!needle) return options;
    return options.filter((option) => option.label.toLowerCase().includes(needle));
}
