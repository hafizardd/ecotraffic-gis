"use client";
import { useEffect, useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { useEmissionsContext } from "@/context/EmissionsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchLatestSegmentEmissions } from "@/services/api";
import { analyticsLiveStatus, isNewerSegment } from "@/utils/emissionAnalytics";
import { fmtDateTimeId, fmtFloatId } from "@/utils/format";
import type { LatestSegmentEmissionsResponse } from "@/types";

export default function RealtimePollutants() {
    const { filter } = useEmissionAnalytics();
    const { segmentEmissionMap, connectionStatus } = useEmissionsContext();
    const [now, setNow] = useState(() => Date.now());
    const [result, setResult] = useState<{ key: string; value?: LatestSegmentEmissionsResponse; error?: string }>({ key: "" });
    const key = `${filter.segmentId ?? ""}:${filter.corridorId ?? ""}`;
    const segmentId = filter.segmentId, corridorId = filter.corridorId;
    useEffect(() => {
        const timer = setInterval(() => setNow(Date.now()), 1000);
        return () => clearInterval(timer);
    }, []);
    useEffect(() => {
        const controller = new AbortController();
        const load = async () => {
            try {
                const value = await fetchLatestSegmentEmissions({ segment_id: segmentId ?? undefined, corridor_id: corridorId ?? undefined }, controller.signal);
                if (!controller.signal.aborted) setResult({ key, value });
            } catch (error) {
                if (!controller.signal.aborted) setResult({ key, error: error instanceof Error ? error.message : "Gagal memuat emisi terkini" });
            }
        };
        // WebSocket invalidates only the live summary. Historical queries retain
        // their own selected time range; backend computes the spatial rollup.
        const debounce = setTimeout(() => void load(), 150);
        const timer = setInterval(() => void load(), 15000);
        return () => { controller.abort(); clearTimeout(debounce); clearInterval(timer); };
    }, [segmentId, corridorId, key, segmentEmissionMap]);
    const loading = result.key !== key;
    const loadedSummary = loading ? undefined : result.value?.summary;
    const liveSegment = segmentId ? segmentEmissionMap.get(segmentId) : undefined;
    const matches = liveSegment && (!corridorId || liveSegment.corridor_id === corridorId)
        && (!loadedSummary?.observed_at || !loadedSummary.processed_at || isNewerSegment(liveSegment, {
            observed_at: loadedSummary.observed_at, processed_at: loadedSummary.processed_at,
        }));
    // For a single selected segment, render the eight rates directly from its
    // WebSocket payload. Multi-segment rollups remain backend calculations.
    const summary = matches ? { ...liveSegment, segment_count: 1,
        estimated_segment_count: liveSegment.quality_status === "estimated" ? 1 : 0 } : loadedSummary;
    const isLoading = loading && !matches;
    const state = analyticsLiveStatus(summary?.observed_at ?? null, summary?.stale_after_seconds ?? 180, summary?.source_mode ?? "", now);
    const age = summary?.observed_at ? Math.max(0, Math.floor((now - Date.parse(summary.observed_at)) / 1000)) : null;
    return <section aria-label="Delapan polutan terkini" aria-busy={isLoading}>
        <div className="card-header analytics-live-header"><strong>Emisi segmen terkini</strong><span className={`analytics-status status-${state.toLowerCase().replace(" ", "-")}`}>{isLoading ? "MEMUAT" : result.error && !matches ? "ERROR" : state}</span></div>
        <p className="analytics-note">{summary?.segment_count ?? 0} segmen · {age === null ? "Menunggu pengamatan" : `Pengamatan tertua ${age} detik lalu`} · WebSocket {connectionStatus}
            {summary?.processed_at ? ` · Diproses ${fmtDateTimeId(summary.processed_at)}` : ""}
            {summary?.estimated_segment_count ? ` · ${summary.estimated_segment_count} segmen estimated (occupancy)` : ""}</p>
        <p className="analytics-note">Nilai terbaru mengikuti filter lokasi. Rentang waktu berlaku untuk visual historis di bawah.</p>
        {!isLoading && result.error && !matches && <p role="alert" className="analytics-error">{result.error}</p>}
        <div className="page-card-grid analytics-pollutants">{EMISSION_DEFINITIONS.map(({ key: pollutant, label }) => {
            const value = summary?.emissions_kg_h[pollutant];
            return <div key={pollutant} className={`page-card summary-metric pollutant-${pollutant}`}>
                <span><i className="pollutant-dot" />{label}</span>
                <strong>{isLoading ? "Memuat…" : value == null ? "—" : fmtFloatId(value, value < 0.01 ? 6 : 3)}</strong>
                <small>kg/hour · {summary?.segment_count ? state : "Tidak ada data"}</small>
            </div>;
        })}</div>
    </section>;
}
