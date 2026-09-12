"use client";
import { useEffect, useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { useEmissionsContext } from "@/context/EmissionsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchLatestSegmentEmissions } from "@/services/api";
import { analyticsLiveStatus, isNewerSegment } from "@/utils/emissionAnalytics";
import { fmtFloatId } from "@/utils/format";
import type { LatestSegmentEmissionsResponse } from "@/types";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";

export default function RealtimePollutants() {
    const { filter } = useEmissionAnalytics();
    const { segmentEmissionMap } = useEmissionsContext();
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
    const meta = isLoading
        ? "Memuat pengamatan terbaru…"
        : `${summary?.segment_count ?? 0} segmen · Pengamatan terakhir ${age === null ? "belum tersedia" : `${age} detik lalu`}${summary?.estimated_segment_count ? ` · ${summary.estimated_segment_count} estimasi` : ""}`;
    return <section aria-label="Delapan polutan terkini" aria-busy={isLoading} className="animate-in">
        <SectionTitle title="Emisi segmen terkini" eyebrow="Data live" meta={meta}
            aside={<span className={`analytics-status status-${state.toLowerCase().replace(" ", "-")}`}>{isLoading ? "Memuat" : result.error && !matches ? "Error" : state}</span>} />
        {!isLoading && result.error && !matches && <p role="alert" className="analytics-error">{result.error}</p>}
        <div className="page-card-grid analytics-pollutants">{isLoading
            ? EMISSION_DEFINITIONS.map(({ key: pollutant }) => <div className="page-card summary-metric" key={pollutant}>
                <Skeleton height={12} width="55%" /><Skeleton height={26} width="80%" /><Skeleton height={10} width="45%" />
            </div>)
            : EMISSION_DEFINITIONS.map(({ key: pollutant, label }) => {
                const value = summary?.emissions_kg_h[pollutant];
                return <div key={pollutant} className={`page-card summary-metric pollutant-${pollutant}`}>
                    <span><i className="pollutant-dot" />{label}</span>
                    <strong>{value == null ? "-" : fmtFloatId(value, value < 0.01 ? 6 : 3)}</strong>
                    <small>kg/hour · {summary?.segment_count ? state : "Tidak ada data"}</small>
                </div>;
            })}</div>
    </section>;
}
