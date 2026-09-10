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
import {
    MISSING_LABEL,
    fmtDateTimeId,
    fmtEmissionId,
    fmtIntId,
    fmtKm,
    fmtPercentId,
    fmtVehicleId,
} from "@/utils/format";

const VEHICLE_TYPES = ["car", "motorcycle", "bus", "truck"] as const;

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
        <aside className="monitoring-panel segment-panel">
            <div className="panel-header">
                <div className="panel-location-icon"><Route aria-hidden="true" /></div>
                <div className="panel-title">
                    <span>SEGMEN TERPILIH</span>
                    <h2>{detail?.name ?? segmentId}</h2>
                </div>
                <button onClick={onClose} className="panel-close" aria-label="Tutup panel segmen"><X aria-hidden="true" /></button>
            </div>
            <div className="panel-content">
                {!detail && !error && <div aria-hidden="true">
                    <div className="segment-overview"><Skeleton height={16} width="62%" /><Skeleton height={14} width="28%" /></div>
                    <section className="panel-section">
                        <Skeleton height={12} width="42%" />
                        <div className="stat-grid" style={{ marginTop: 14 }}>{Array.from({ length: 8 }, (_, index) => (
                            <div className="stat-card" key={index}><Skeleton height={10} width="56%" /><Skeleton height={18} width="72%" /></div>
                        ))}</div>
                    </section>
                </div>}
                {error && <div className="segment-state error-state"><strong>Data segmen tidak tersedia</strong><span>{error.message}</span></div>}
                {liveDetail && (
                    <>
                        <div className="segment-update-status" aria-live="polite">
                            {liveDetail.calculated_at
                                ? `Diperbarui ${fmtDateTimeId(liveDetail.calculated_at)}${liveDetail.freshness_status ? ` · Data: ${liveDetail.freshness_status}` : ""}`
                                : "Belum ada perhitungan emisi"}
                        </div>
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
        ? `Estimasi dari CCTV ${fallback.camId}`
        : detail.volume_status === "estimated"
            ? "Estimasi CCTV"
            : detail.calculated_at
                ? "Terukur"
                : "Belum ada perhitungan";
    return (
        <>
            <div className="segment-overview">
                <strong>{detail.road_segment_id}</strong>
                <span>{fmtKm(detail.length_km)}</span>
            </div>
            <section className="panel-section segment-emission-section">
                <SectionTitle title="Emisi segmen" meta={`Nilai agregat dalam g/jam · ${sourceBadge}`} />
                {hasAny && shown ? (
                    <div className="stat-grid">
                        {EMISSION_DEFINITIONS.map(({ key, label }) => (
                            <div className={`stat-card pollutant-${key}`} key={key}>
                                <span className="stat-label"><i className="pollutant-dot" />{label}</span>
                                <strong className={`stat-value${shown[key] == null ? " data-missing" : ""}`}>{fmtEmissionId(shown[key])}</strong>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="data-empty">Belum ada perhitungan emisi — data CCTV belum teragregasi</p>
                )}
                {fallback && !hasEmission && (
                    <p className="segment-note">Estimasi dari CCTV {fallback.camId} — bukan volume per jam terukur{fallback.at ? ` · ${fmtDateTimeId(fallback.at)}` : ""}</p>
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
        <section className="panel-section segment-population-section">
            <SectionTitle title="Populasi wilayah" meta="Konteks administratif segmen" />
            {!primary && intersecting.length === 0 && <p className="data-empty">{MISSING_LABEL}</p>}
            {primary && (
                <dl className="population-summary">
                    <div>
                        <dt>Kecamatan</dt>
                        <dd className={primary.district_name == null ? "data-missing" : undefined}>{primary.district_name ?? MISSING_LABEL}</dd>
                    </div>
                    <div className="population-value">
                        <dt>Populasi wilayah</dt>
                        <dd className={primary.population == null ? "data-missing" : undefined}>{formatPopulation(primary.population)}</dd>
                    </div>
                    <div className="population-method">
                        <dt>Metode</dt>
                        <dd className={primary.method == null ? "data-missing" : undefined}>{primary.method ?? MISSING_LABEL}</dd>
                    </div>
                </dl>
            )}
            {intersecting.length > 0 && (
                <details className="population-boundaries">
                    <summary>Wilayah berbatasan ({fmtIntId(intersecting.length)})</summary>
                    {intersecting.map((zone, index) => (
                        <div className="population-boundary" key={index}>
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
            <section className="panel-section segment-activity-section">
                <SectionTitle title="Potensi aktivitas" meta="Grid heksagon (AHP)" />
                <Skeleton height={16} width="62%" />
                <Skeleton height={14} width="28%" />
            </section>
        );
    }
    if (!feature) {
        return (
            <section className="panel-section segment-activity-section">
                <SectionTitle title="Potensi aktivitas" meta="Grid heksagon (AHP)" />
                <p className="data-empty">Segmen ini belum tercakup dalam grid potensi aktivitas</p>
            </section>
        );
    }
    return (
        <section className="panel-section segment-activity-section">
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
            <section className="panel-section segment-vehicle-section">
                <SectionTitle title={title} meta={subtitle} aside={estimated ? <b className="estimate-badge">Estimasi</b> : undefined} />
                <p className="data-empty">{unavailableLabel}</p>
            </section>
        );
    }
    return (
        <section className="panel-section segment-vehicle-section">
            <SectionTitle title={title} meta={subtitle} aside={estimated ? <b className="estimate-badge">Estimasi</b> : undefined} />
            <div className="vehicle-summary">
                {VEHICLE_TYPES.map((key) => {
                    const value = values?.[key];
                    return <div key={key}><span>{key}</span><strong className={value == null ? "data-missing" : undefined}>{value == null ? MISSING_LABEL : fmtVehicleId(Number(value))}</strong></div>;
                })}
            </div>
        </section>
    );
}
