"use client";
import { useEffect, useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { useEmissionsContext } from "@/context/EmissionsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchLatestSegmentEmissions } from "@/services/api";
import { analyticsLiveStatus, isNewerSegment } from "@/utils/emissionAnalytics";
import { fmtDateTimeId, fmtFloatId } from "@/utils/format";
import type { LatestSegmentEmissionsResponse } from "@/types";
import AnalyticsMeasureBand from "@/components/Analytics/AnalyticsMeasureBand";
import AnalyticsMetricLedger from "@/components/Analytics/AnalyticsMetricLedger";
import SectionTitle from "@/components/ui/SectionTitle";
import { ANALYTICS_ERROR_CLASS, ANIMATE_IN_CLASS } from "@/styles/tailwind";

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
    const statusClass = state === "LIVE" ? "bg-[#123525] text-[#4ade80]" : state === "STALE" ? "bg-[#3c3018] text-[#fbbf24]" : "bg-[#334155] text-[#cbd5e1]";
    const statusTone = state === "LIVE" ? "live" : state === "STALE" ? "stale" : "default";
    const metrics = EMISSION_DEFINITIONS.map(({ key: pollutant, label, color }) => {
        const value = summary?.emissions_kg_h[pollutant];
        return {
            key: pollutant,
            label,
            color,
            value: value == null ? "–" : fmtFloatId(value, value < 0.01 ? 6 : 3),
            unit: "kg/hour",
            meta: summary?.segment_count ? state : "Tidak ada data",
        };
    });
    return <section aria-label="Delapan polutan terkini" aria-busy={isLoading} className={ANIMATE_IN_CLASS}>
        <SectionTitle title="Emisi segmen terkini" eyebrow="Data live" meta="Laju massa terbaru dari cakupan segmen aktif."
            aside={<span className={`rounded px-2.25 py-1.25 text-[11px] font-bold ${statusClass}`}>{isLoading ? "Memuat" : result.error && !matches ? "Error" : state}</span>} />
        {!isLoading && result.error && !matches && <p role="alert" className={ANALYTICS_ERROR_CLASS}>{result.error}</p>}
        <AnalyticsMeasureBand items={[
            { label: "Sumber", value: isLoading ? "Memuat" : summary?.source_mode ?? "Belum tersedia", tone: statusTone },
            { label: "Segmen", value: isLoading ? "–" : summary?.segment_count ?? 0 },
            { label: "Teramati", value: isLoading ? "–" : fmtDateTimeId(summary?.observed_at) },
            { label: "Usia data", value: isLoading || age === null ? "–" : `${age} detik`, tone: statusTone },
            { label: "Estimasi", value: isLoading ? "–" : summary?.estimated_segment_count ?? 0, tone: summary?.estimated_segment_count ? "estimated" : "default" },
        ]} />
        <AnalyticsMetricLedger label="Laju delapan polutan terkini" loading={isLoading} items={metrics} />
    </section>;
}
