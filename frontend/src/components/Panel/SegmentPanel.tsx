"use client";

import { useEffect, useMemo, useState } from "react";
import { Route, X } from "lucide-react";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchSegmentActivityGrid, fetchSegmentEmission } from "@/services/api";
import { ActivityGridFeature, EmissionUpdate, SegmentEmissionDetail } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import ActivityPotentialCard from "@/components/Panel/ActivityPotentialCard";
import AutoInsightCard from "@/components/Panel/AutoInsightCard";
import {
    MISSING_LABEL,
    fmtDateTimeId,
    fmtEmissionId,
    fmtIntId,
    fmtKm,
    fmtPercentId,
    fmtVehicleId,
    formatCameraName,
    formatMethodLabel,
} from "@/utils/format";
import { DATA_EMPTY_CLASS, ESTIMATE_BADGE_CLASS, PANEL_CLASS, PANEL_CLOSE_CLASS, PANEL_CONTENT_CLASS, PANEL_ICON_CLASS, POLLUTANT_DOT_CLASS, POLLUTANT_TEXT_CLASS, STAT_CARD_CLASS, STAT_GRID_CLASS } from "@/styles/tailwind";

const VEHICLE_TYPES = ["car", "motorcycle", "bus", "truck"] as const;
const SEGMENT_SECTION_CLASS = "border-b border-[rgba(148,163,184,0.1)] px-4 py-5 last:border-b-0 max-[420px]:px-[14px] max-[420px]:py-[18px]";
const SEGMENT_OVERVIEW_CLASS = "mx-4 mt-[10px] grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-[10px] gap-y-1.5 rounded-[9px] border border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.88)] px-[13px] py-3 max-[420px]:mx-[14px] [&>strong]:min-w-0 [&>strong]:text-sm [&>strong]:leading-[1.35] [&>strong]:[overflow-wrap:anywhere] [&>span]:whitespace-nowrap [&>span]:text-right [&>span]:text-[11px] [&>span]:leading-[1.35] [&>span]:text-[var(--secondary)]";
const SEGMENT_EMPTY_CLASS = `${DATA_EMPTY_CLASS} m-0 min-h-[58px] border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.4)] p-[13px] text-center text-[10px] leading-[1.5] text-[#718198]`;
const DATA_MISSING_CLASS = "text-[10px]! font-medium! leading-[1.4]! tracking-normal! text-[#718198]!";
const VEHICLE_SUMMARY_CLASS = "grid grid-cols-2 gap-[9px] max-[420px]:grid-cols-1 [&>div]:flex [&>div]:min-h-[50px] [&>div]:min-w-0 [&>div]:items-baseline [&>div]:justify-between [&>div]:gap-2 [&>div]:rounded-[7px] [&>div]:border [&>div]:border-[rgba(148,163,184,0.1)] [&>div]:bg-[rgba(14,29,46,0.75)] [&>div]:p-[11px] [&>div]:tabular-nums [&>div]:[overflow-wrap:anywhere] [&_span]:text-[10px] [&_span]:leading-[1.3] [&_span]:text-[#7f8fa5] [&_strong]:text-right [&_strong]:text-sm [&_strong]:leading-[1.35] [&_strong]:text-[#e2e8f0] [&_strong]:tabular-nums [&_strong]:[overflow-wrap:anywhere]";

export default function SegmentPanel({
    segmentId,
    onClose,
}: {
    segmentId: string | null;
    onClose: () => void;
}) {
    if (!segmentId) return null;
    return <SegmentDetailPanel key={segmentId} segmentId={segmentId} onClose={onClose} />;
}

function SegmentDetailPanel({
    segmentId,
    onClose,
}: {
    segmentId: string;
    onClose: () => void;
}) {
    const [detail, setDetail] = useState<SegmentEmissionDetail | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const { segmentMap, emissionMap } = useEmissionsContext();

    useEffect(() => {
        let mounted = true;
        fetchSegmentEmission(segmentId)
            .then((value) => mounted && setDetail(value))
            .catch((err) => mounted && setError(err instanceof Error ? err : new Error("Data segmen tidak tersedia")));
        return () => {
            mounted = false;
        };
    }, [segmentId]);
    const update = segmentMap.get(segmentId);
    const liveDetail = useMemo(() => {
        if (!detail) return detail;
        if (!update) return detail;
        return {
            ...detail,
            pollutant_totals_g_h: update.pollutant_totals ?? detail.pollutant_totals_g_h,
            volume_per_hour: update.volume_per_hour ?? detail.volume_per_hour,
            population_context: update.population_context ?? detail.population_context,
            population: update.population ?? detail.population,
            population_district: update.population_district ?? detail.population_district,
            freshness_status: update.freshness_status ?? detail.freshness_status,
            calculated_at: update.calculated_at ?? detail.calculated_at,
        };
    }, [detail, update]);

    const fallback = (() => {
        if (!liveDetail) return null;
        if (liveDetail.pollutant_totals_g_h != null || liveDetail.volume_per_hour != null) return null;
        const cameras: string[] = Array.isArray((liveDetail.provenance as { source_cameras?: unknown })?.source_cameras)
            ? ((liveDetail.provenance as { source_cameras: string[] }).source_cameras ?? [])
            : [];
        for (const camId of cameras) {
            const live: EmissionUpdate | undefined = emissionMap.get(camId);
            const emission = live?.instant_emission ?? live?.occupancy;
            if (live && emission) return { camId, emission, at: live.captured_at ?? live.timestamp };
        }
        return null;
    })();

    return (
        <aside className={PANEL_CLASS}>
            <div className="flex min-h-[68px] flex-[0_0_auto] items-center gap-[10px] border-b border-[rgba(148,163,184,0.12)] px-[14px] py-[9px]">
                <div className={`${PANEL_ICON_CLASS} flex-[0_0_auto]`}><Route aria-hidden="true" /></div>
                <div className="min-w-0 flex-1 [&>span]:text-[8px] [&>span]:font-bold [&>span]:leading-none [&>span]:tracking-[0.13em] [&>span]:text-[var(--muted)] [&>h2]:mt-1 [&>h2]:mb-0 [&>h2]:line-clamp-2 [&>h2]:font-[var(--font-display)] [&>h2]:text-sm [&>h2]:font-[650] [&>h2]:leading-[1.25] [&>h2]:[overflow-wrap:anywhere]">
                    <span>SEGMEN TERPILIH</span>
                    <h2>{detail?.name ?? segmentId}</h2>
                </div>
                <button onClick={onClose} className={`${PANEL_CLOSE_CLASS} m-0 bg-[#0b1a2a]`} aria-label="Tutup panel segmen"><X aria-hidden="true" /></button>
            </div>
            <div className={`${PANEL_CONTENT_CLASS} pb-1 [scrollbar-color:#34455b_transparent] [scrollbar-gutter:stable] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:border-2 [&::-webkit-scrollbar-thumb]:border-[#081522] [&::-webkit-scrollbar-thumb]:bg-[#34455b] hover:[&::-webkit-scrollbar-thumb]:bg-[#465a73]`}>
                {!detail && !error && <div aria-hidden="true">
                    <div className={SEGMENT_OVERVIEW_CLASS}><Skeleton height={16} width="62%" /><Skeleton height={14} width="28%" /></div>
                    <section className={SEGMENT_SECTION_CLASS}>
                        <Skeleton height={12} width="42%" />
                        <div className={`${STAT_GRID_CLASS} mt-[14px] gap-[9px]`}>{Array.from({ length: 8 }, (_, index) => (
                            <div className={`${STAT_CARD_CLASS} flex min-h-[84px] min-w-0 flex-col justify-between border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.82)] p-3`} key={index}><Skeleton height={10} width="56%" /><Skeleton height={18} width="72%" /></div>
                        ))}</div>
                    </section>
                </div>}
                {error && <div className="flex min-h-[150px] flex-col items-center justify-center gap-[9px] p-4 text-center text-[11px] leading-[1.5] text-[var(--secondary)] [&>strong]:text-[#f87171] [&>span]:text-[10px]"><strong>Data segmen tidak tersedia</strong><span>{error.message}</span></div>}
                {liveDetail && (
                    <>
                        <div className="mx-4 mt-3 rounded-[0_6px_6px_0] border-l-2 border-[rgba(74,222,128,0.5)] bg-[rgba(15,29,46,0.62)] px-[10px] py-2 text-[10px] leading-[1.45] text-[#8292a8] max-[420px]:mx-[14px]" aria-live="polite">
                            {liveDetail.calculated_at
                                ? `Diperbarui ${fmtDateTimeId(liveDetail.calculated_at)}`
                                : "Belum ada perhitungan emisi"}
                        </div>
                        <AutoInsightCard entity={{ type: "segment", id: liveDetail.road_segment_id }} label={liveDetail.name} />
                        <SegmentDetails detail={liveDetail} fallback={fallback} />
                    </>
                )}
            </div>
        </aside>
    );
}

type Fallback = { camId: string; emission: Record<string, number>; at?: string } | null;

// Backend segment totals use UPPERCASE keys (TSP, NOx, ...); camera
// instant_emission uses total_<key>_g_per_min / total_<key>_kg_per_hr.
// Normalize once per render so card lookups (lowercase keys) resolve.
function normalizePollutantTotals(totals: Record<string, number> | null | undefined): Record<string, number> {
    const norm: Record<string, number> = {};
    for (const [rawKey, rawValue] of Object.entries(totals ?? {})) {
        const value = Number(rawValue);
        if (!Number.isFinite(value)) continue;
        const lower = rawKey.toLowerCase();
        if (lower.endsWith("_kg_per_hr")) {
            // kg/jam -> g/jam; preferred over the per-minute rate when both present.
            norm[lower.replace(/^total_/, "").replace(/_kg_per_hr$/, "")] = value * 1000;
        } else if (lower.endsWith("_g_per_min") || lower.endsWith("_g_per_hr")) {
            norm[lower.replace(/^total_/, "").replace(/_g_per_(min|hr)$/, "")] ??= value;
        } else {
            norm[lower] ??= value;
        }
    }
    return norm;
}

function SegmentDetails({ detail, fallback }: { detail: SegmentEmissionDetail; fallback?: Fallback }) {
    const hasEmission = detail.pollutant_totals_g_h != null;
    const totals = useMemo(
        () => normalizePollutantTotals(detail.pollutant_totals_g_h),
        [detail.pollutant_totals_g_h],
    );
    const fallbackTotals = useMemo(
        () => (fallback ? normalizePollutantTotals(fallback.emission) : null),
        [fallback],
    );
    const shown = hasEmission ? totals : fallbackTotals;
    const hasAny = shown != null && EMISSION_DEFINITIONS.some(({ key }) => shown[key] != null);
    const sourceBadge = !hasEmission && fallback
        ? `Estimasi dari CCTV ${formatCameraName(fallback.camId)}`
        : detail.volume_status === "estimated"
            ? "Estimasi CCTV"
            : detail.calculated_at
                ? "Terukur"
                : "Belum ada perhitungan";
    return (
        <>
            <div className={SEGMENT_OVERVIEW_CLASS}>
                <strong>{detail.road_segment_id}</strong>
                <span>{fmtKm(detail.length_km)}</span>
            </div>
            <section className={SEGMENT_SECTION_CLASS}>
                <SectionTitle title="Emisi segmen" meta={`Nilai agregat dalam g/jam · ${sourceBadge}`} />
                {hasAny && shown ? (
                    <div className={`${STAT_GRID_CLASS} gap-[9px]`}>
                        {EMISSION_DEFINITIONS.map(({ key, label }) => (
                            <div className={`${STAT_CARD_CLASS} flex min-h-[84px] min-w-0 flex-col justify-between border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.82)] p-3 ${POLLUTANT_TEXT_CLASS[key]}`} key={key}>
                                <span className="flex items-center gap-1.5 text-[10px] font-extrabold leading-[1.2] tracking-[0.04em]"><i className={POLLUTANT_DOT_CLASS} />{label}</span>
                                <strong className={`mt-[10px] block w-full text-right text-[clamp(13px,1.15vw,17px)] leading-[1.3] tracking-[-0.02em] text-[#f1f5f9] tabular-nums [overflow-wrap:anywhere] ${shown[key] == null ? DATA_MISSING_CLASS : ""}`}>{fmtEmissionId(shown[key])}</strong>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className={SEGMENT_EMPTY_CLASS}>Belum ada perhitungan emisi. Data CCTV belum teragregasi.</p>
                )}
                {fallback && !hasEmission && (
                    <p className="mt-[10px] mb-0 rounded-[0_6px_6px_0] border-l-2 border-[rgba(245,165,36,0.42)] bg-[rgba(245,165,36,0.055)] px-[10px] py-[9px] text-[10px] leading-[1.5] text-[#8292a8]">Estimasi dari CCTV {formatCameraName(fallback.camId)}, bukan volume per jam terukur{fallback.at ? `, ${fmtDateTimeId(fallback.at)}` : ""}.</p>
                )}
            </section>
            <PopulationSection context={detail.population_context} />
            <ActivityPotentialSection segmentId={detail.road_segment_id} />
            <VehicleMetrics title="VOLUME KENDARAAN" subtitle="Agregat per jam" values={detail.volume_per_hour} estimated={detail.volume_status === "estimated"} unavailableLabel="Volume belum tersedia dari snapshot occupancy" />
            <VehicleMetrics title="VKT" subtitle="Kendaraan-kilometer per jam" values={detail.vkt_km_h} estimated={detail.volume_status === "estimated"} unavailableLabel="VKT belum tersedia dari snapshot occupancy" />
        </>
    );
}

function PopulationSection({ context }: { context: SegmentEmissionDetail["population_context"] }) {
    const primary = context?.primary;
    const intersecting = context?.intersecting ?? [];
    const formatPopulation = (value: number | null | undefined) => value == null ? MISSING_LABEL : `${fmtIntId(value)} jiwa`;
    return (
        <section className={SEGMENT_SECTION_CLASS}>
            <SectionTitle title="Populasi wilayah" meta="Konteks administratif segmen" />
            {!primary && intersecting.length === 0 && <p className={SEGMENT_EMPTY_CLASS}>{MISSING_LABEL}</p>}
            {primary && (
                <dl className="m-0 grid grid-cols-2 gap-[9px] max-[420px]:grid-cols-1 [&>div]:min-w-0 [&>div]:rounded-[7px] [&>div]:border [&>div]:border-[rgba(148,163,184,0.1)] [&>div]:bg-[rgba(14,29,46,0.75)] [&>div]:px-3 [&>div]:py-[11px] [&_dt]:text-[9px] [&_dt]:font-bold [&_dt]:leading-[1.2] [&_dt]:tracking-[0.05em] [&_dt]:text-[#718198] [&_dt]:uppercase [&_dd]:mt-1.5 [&_dd]:mb-0 [&_dd]:text-[13px] [&_dd]:font-[650] [&_dd]:leading-[1.35] [&_dd]:text-[#dbeafe] [&_dd]:[overflow-wrap:anywhere]">
                    <div>
                        <dt>Kecamatan</dt>
                        <dd className={primary.district_name == null ? DATA_MISSING_CLASS : undefined}>{primary.district_name ?? MISSING_LABEL}</dd>
                    </div>
                    <div className="[&>dd]:text-base [&>dd]:text-[#f1f5f9] [&>dd]:tabular-nums">
                        <dt>Populasi wilayah</dt>
                        <dd className={primary.population == null ? DATA_MISSING_CLASS : undefined}>{formatPopulation(primary.population)}</dd>
                    </div>
                    <div className="col-span-full max-[420px]:col-auto [&>dd]:text-[11px] [&>dd]:font-medium [&>dd]:text-[#94a3b8]">
                        <dt>Metode</dt>
                        <dd className={primary.method == null ? DATA_MISSING_CLASS : undefined}>{formatMethodLabel(primary.method)}</dd>
                    </div>
                </dl>
            )}
            {intersecting.length > 0 && (
                <details className="mt-[14px] border-t border-[rgba(148,163,184,0.09)] pt-[13px] text-[10px] leading-[1.45] text-[#8292a8] marker:text-[#64748b]">
                    <summary className="cursor-pointer text-[10px] font-bold text-[#aab8ca]">Wilayah berbatasan ({fmtIntId(intersecting.length)})</summary>
                    {intersecting.map((zone, index) => (
                        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] items-start gap-[10px] border-b border-[rgba(148,163,184,0.07)] px-px py-[9px] last:border-b-0 last:pb-0 max-[420px]:grid-cols-1 max-[420px]:gap-[3px] [&>strong]:text-[10px] [&>strong]:leading-[1.4] [&>strong]:text-[#cbd5e1] [&>strong]:[overflow-wrap:anywhere] [&>span]:text-right [&>span]:text-[10px] [&>span]:leading-[1.45] [&>span]:text-[#718198] [&>span]:tabular-nums [&>span]:[overflow-wrap:anywhere] max-[420px]:[&>span]:text-left" key={index}>
                            <strong>{zone.district_name}</strong>
                            <span>{formatPopulation(zone.population)} · {zone.overlap_share == null ? MISSING_LABEL : `${fmtPercentId(zone.overlap_share, 0)}`} tumpang tindih</span>
                        </div>
                    ))}
                </details>
            )}
        </section>
    );
}

function ActivityPotentialSection({ segmentId }: { segmentId: string }) {
    const [feature, setFeature] = useState<ActivityGridFeature | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let mounted = true;
        fetchSegmentActivityGrid(segmentId)
            .then((value) => { if (mounted) { setFeature(value); setLoading(false); } })
            .catch(() => { if (mounted) setLoading(false); });
        return () => { mounted = false; };
    }, [segmentId]);

    if (loading) {
        return (
            <section className={SEGMENT_SECTION_CLASS}>
                <SectionTitle title="Potensi aktivitas" meta="Grid heksagon (AHP)" />
                <Skeleton height={16} width="62%" />
                <Skeleton height={14} width="28%" />
            </section>
        );
    }
    if (!feature) {
        return (
            <section className={SEGMENT_SECTION_CLASS}>
                <SectionTitle title="Potensi aktivitas" meta="Grid heksagon (AHP)" />
                <p className={SEGMENT_EMPTY_CLASS}>Segmen ini belum tercakup dalam grid potensi aktivitas</p>
            </section>
        );
    }
    return (
        <section className={SEGMENT_SECTION_CLASS}>
            <SectionTitle title="Potensi aktivitas" meta="Grid heksagon (AHP)" />
            <ActivityPotentialCard properties={feature.properties} />
        </section>
    );
}

function VehicleMetrics({
    title,
    subtitle,
    values,
    estimated,
    unavailableLabel,
}: {
    title: string;
    subtitle: string;
    values: Record<string, number> | null;
    estimated: boolean;
    unavailableLabel: string;
}) {
    if (values == null) {
        return (
            <section className={SEGMENT_SECTION_CLASS}>
                <SectionTitle title={title} meta={subtitle} aside={estimated ? <b className={ESTIMATE_BADGE_CLASS}>Estimasi</b> : undefined} />
                <p className={SEGMENT_EMPTY_CLASS}>{unavailableLabel}</p>
            </section>
        );
    }
    return (
        <section className={SEGMENT_SECTION_CLASS}>
            <SectionTitle title={title} meta={subtitle} aside={estimated ? <b className={ESTIMATE_BADGE_CLASS}>Estimasi</b> : undefined} />
            <div className={VEHICLE_SUMMARY_CLASS}>
                {VEHICLE_TYPES.map((key) => {
                    const value = values?.[key];
                    return <div key={key}><span>{key}</span><strong className={value == null ? DATA_MISSING_CLASS : undefined}>{value == null ? MISSING_LABEL : fmtVehicleId(Number(value))}</strong></div>;
                })}
            </div>
        </section>
    );
}
