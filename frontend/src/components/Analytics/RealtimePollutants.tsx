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
import { ANALYTICS_ERROR_CLASS, ANIMATE_IN_CLASS, PAGE_CARD_CLASS, PAGE_CARD_GRID_CLASS, POLLUTANT_DOT_CLASS, POLLUTANT_TEXT_CLASS, SUMMARY_METRIC_CLASS } from "@/styles/tailwind";

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
    const statusClass = state === "LIVE" ? "bg-[#123525] text-[#4ade80]" : state === "STALE" ? "bg-[#3c3018] text-[#fbbf24]" : "bg-[#334155] text-[#cbd5e1]";
    return <section aria-label="Delapan polutan terkini" aria-busy={isLoading} className={ANIMATE_IN_CLASS}>
        <SectionTitle title="Emisi segmen terkini" eyebrow="Data live" meta={meta}
            aside={<span className={`rounded px-[9px] py-[5px] text-[11px] font-bold ${statusClass}`}>{isLoading ? "Memuat" : result.error && !matches ? "Error" : state}</span>} />
        {!isLoading && result.error && !matches && <p role="alert" className={ANALYTICS_ERROR_CLASS}>{result.error}</p>}
        <div className={`${PAGE_CARD_GRID_CLASS} mt-[14px] grid-cols-4 max-[600px]:grid-cols-2`}>{isLoading
            ? EMISSION_DEFINITIONS.map(({ key: pollutant }) => <div className={`${PAGE_CARD_CLASS} ${SUMMARY_METRIC_CLASS}`} key={pollutant}>
                <Skeleton height={12} width="55%" /><Skeleton height={26} width="80%" /><Skeleton height={10} width="45%" />
            </div>)
            : EMISSION_DEFINITIONS.map(({ key: pollutant, label }) => {
                const value = summary?.emissions_kg_h[pollutant];
                return <div key={pollutant} className={`${PAGE_CARD_CLASS} ${SUMMARY_METRIC_CLASS} ${POLLUTANT_TEXT_CLASS[pollutant]}`}>
                    <span className="flex items-center gap-1.5"><i className={POLLUTANT_DOT_CLASS} />{label}</span>
                    <strong className="text-[clamp(18px,2vw,27px)]!">{value == null ? "-" : fmtFloatId(value, value < 0.01 ? 6 : 3)}</strong>
                    <small>kg/hour · {summary?.segment_count ? state : "Tidak ada data"}</small>
                </div>;
            })}</div>
    </section>;
}
