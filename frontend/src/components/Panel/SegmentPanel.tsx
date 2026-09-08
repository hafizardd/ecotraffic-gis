"use client";

import { useEffect, useMemo, useState } from "react";
import { Route, X } from "lucide-react";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchSegmentEmission } from "@/services/api";
import { EmissionUpdate, SegmentEmissionDetail } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";
import {
    MISSING_LABEL,
    fmtDateTimeId,
    fmtEmissionId,
    fmtFloatId,
    fmtIntId,
    fmtKm,
    fmtPercentId,
    fmtSpatialStatus,
    fmtVehicleId,
} from "@/utils/format";

const VEHICLE_TYPES = ["car", "motorcycle", "bus", "truck"] as const;
const CRITERIA_ORDER = ["K1", "K2", "K3", "K4", "K5"] as const;

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
            decision_score: update.decision_score ?? detail.decision_score,
            priority: update.priority ?? detail.priority,
            pollutant_totals_g_h: update.pollutant_totals ?? detail.pollutant_totals_g_h,
            volume_per_hour: update.volume_per_hour ?? detail.volume_per_hour,
            population_context: update.population_context ?? detail.population_context,
            population: update.population ?? detail.population,
            population_district: update.population_district ?? detail.population_district,
            freshness_status: update.freshness_status ?? detail.freshness_status,
            calculated_at: update.calculated_at ?? detail.calculated_at,
            spatial_criteria_status: update.spatial_criteria_status ?? detail.spatial_criteria_status,
        };
    }, [detail, update]);

    const fallback = useMemo(() => {
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
    }, [liveDetail, emissionMap]);

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
                {!detail && !error && <div className="segment-state"><span className="loading-spinner" />Memuat detail segmen...</div>}
                {error && <div className="segment-state error-state"><strong>Data segmen tidak tersedia</strong><span>{error.message}</span></div>}
                {liveDetail && <><div className="segment-state">{liveDetail.calculated_at ? `Diperbarui ${fmtDateTimeId(liveDetail.calculated_at)}${liveDetail.freshness_status ? ` · Data: ${liveDetail.freshness_status}` : ""}` : "Belum ada perhitungan emisi"}</div><SegmentDetails detail={liveDetail} fallback={fallback} /></>}
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
            <div className="segment-overview" title={`Skor: ${detail.decision_score ?? "-"} · Status: ${detail.spatial_criteria_status}`}>
                <strong>{detail.road_segment_id}</strong>
                <span>{fmtKm(detail.length_km)}</span>
                <b className={`priority-badge priority-${detail.priority ?? "unknown"}`}>
                    {detail.priority ?? "Belum dinilai"}
                </b>
            </div>
            <section className="panel-section">
                <div className="section-heading"><div><span>EMISI SEGMEN</span><small>Nilai agregat dalam g/jam · {sourceBadge}</small></div></div>
                {hasAny && shown ? (
                    <div className="stat-grid">
                        {EMISSION_DEFINITIONS.map(({ key, label }) => (
                            <div className={`stat-card pollutant-${key}`} key={key}>
                                <span className="stat-label"><i className="pollutant-dot" />{label}</span>
                                <strong className="stat-value">{fmtEmissionId(shown[key])}</strong>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="data-empty">Belum ada perhitungan emisi — data CCTV belum teragregasi</p>
                )}
                {fallback && !hasEmission && (
                    <p className="data-empty">Estimasi dari CCTV {fallback.camId} — bukan volume per jam terukur{fallback.at ? ` · ${fmtDateTimeId(fallback.at)}` : ""}</p>
                )}
            </section>
            <section className="panel-section">
                <div className="segment-score"><span>DECISION SCORE</span><strong>{detail.decision_score == null ? MISSING_LABEL : fmtFloatId(detail.decision_score, 2)}</strong></div>
                <p className="criteria-status">Kriteria spasial: {fmtSpatialStatus(detail.spatial_criteria_status)}</p>
                <div className="criteria-grid">{CRITERIA_ORDER.map((key) => {
                    const value = (detail.raw_criteria as Record<string, unknown> | null)?.[key] as number | null | undefined;
                    const text = value == null ? MISSING_LABEL : key === "K1" || key === "K2" ? fmtEmissionId(Number(value)) : fmtFloatId(Number(value), 2);
                    return <div key={key}><span>{key}</span><strong>{text}</strong></div>;
                })}</div>
            </section>
            <PopulationSection context={detail.population_context} />
            <SpatialCriteriaSection details={detail.spatial_criteria_details} ahpMetadata={detail.ahp_metadata} rawCriteria={detail.raw_criteria ?? {}} />
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
        <section className="panel-section">
            <div className="section-heading"><div><span>POPULASI WILAYAH</span><small>Konteks administratif segmen</small></div></div>
            {!primary && intersecting.length === 0 && <p className="data-empty">{MISSING_LABEL}</p>}
            {primary && (
                <>
                    <p><strong>Kecamatan:</strong> {primary.district_name ?? MISSING_LABEL}</p>
                    <p><strong>Populasi wilayah:</strong> {formatPopulation(primary.population)}</p>
                    <p><strong>Metode:</strong> {primary.method ?? MISSING_LABEL}</p>
                </>
            )}
            {intersecting.length > 0 && (
                <details>
                    <summary>Wilayah berbatasan ({fmtIntId(intersecting.length)})</summary>
                    {intersecting.map((zone, index) => (
                        <p key={index}><strong>{zone.district_name}:</strong> {formatPopulation(zone.population)} — {zone.overlap_share == null ? MISSING_LABEL : `${fmtPercentId(zone.overlap_share, 0)}`} tumpang tindih</p>
                    ))}
                </details>
            )}
        </section>
    );
}

interface SpatialCriterionDetail {
    nearby_observation_count?: number;
    composite_stop_score?: number;
    poi_count?: number;
    weighted_poi_count?: number;
    buffer_distance_m?: number;
    scoring_version?: string;
    method?: string;
}

function SpatialCriteriaSection({ details, ahpMetadata, rawCriteria }: { details: SegmentEmissionDetail["spatial_criteria_details"]; ahpMetadata: SegmentEmissionDetail["ahp_metadata"]; rawCriteria: Record<string, unknown> }) {
    const detailsRecord = details as Record<string, SpatialCriterionDetail> | undefined;
    const k3 = detailsRecord?.["K3"];
    const k4 = detailsRecord?.["K4"];
    const k5 = detailsRecord?.["K5"];
    const normalized = (ahpMetadata as Record<string, unknown> | undefined)?.["normalized_values"] as Record<string, number> | undefined;
    return (
        <section className="panel-section">
            <div className="section-heading"><div><span>KRITERIA SPASIAL</span><small>K3, K4, K5</small></div></div>
            <div className="criterion-card"><span>K3 — Akses Halte</span><strong>{rawCriteria["K3"] == null ? MISSING_LABEL : fmtFloatId(Number(rawCriteria["K3"]), 2)}</strong><small>Survei terdekat: {k3?.nearby_observation_count == null ? MISSING_LABEL : fmtIntId(k3.nearby_observation_count)} · Skor halte: {k3?.composite_stop_score == null ? MISSING_LABEL : fmtFloatId(Number(k3.composite_stop_score), 2)} · Versi: {k3?.scoring_version ?? MISSING_LABEL}</small></div>
            <div className="criterion-card"><span>K4 — Aktivitas</span><strong>{rawCriteria["K4"] == null ? MISSING_LABEL : fmtFloatId(Number(rawCriteria["K4"]), 2)}</strong><small>POI dalam buffer: {k4?.poi_count == null ? MISSING_LABEL : fmtIntId(k4.poi_count)} · Berbobot: {k4?.weighted_poi_count == null ? MISSING_LABEL : fmtIntId(k4.weighted_poi_count)} · Buffer: {k4?.buffer_distance_m == null ? MISSING_LABEL : `${fmtIntId(k4.buffer_distance_m)} m`}</small></div>
            <div className="criterion-card"><span>K5 — Populasi (est.)</span><strong>{rawCriteria["K5"] == null ? MISSING_LABEL : fmtFloatId(Number(rawCriteria["K5"]), 2)}</strong><small>{k5?.method ?? MISSING_LABEL} · Sumber tingkat kecamatan (perkiraan, bukan jumlah pasti di sepanjang jalan)</small></div>
            {normalized && (
                <div className="criteria-grid">{Object.entries(normalized).map(([key, value]) => <div key={key}><span>{key} (norm)</span><strong>{value == null ? MISSING_LABEL : fmtFloatId(Number(value), 2)}</strong></div>)}</div>
            )}
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
            <section className="panel-section">
                <div className="section-heading"><div><span>{title}</span><small>{subtitle}</small></div>{estimated && <b className="estimate-badge">Estimasi</b>}</div>
                <p className="data-empty">{unavailableLabel}</p>
            </section>
        );
    }
    return (
        <section className="panel-section">
            <div className="section-heading"><div><span>{title}</span><small>{subtitle}</small></div>{estimated && <b className="estimate-badge">Estimasi</b>}</div>
            <div className="vehicle-summary">
                {VEHICLE_TYPES.map((key) => {
                    const value = values?.[key];
                    return <div key={key}><span>{key}</span><strong>{value == null ? MISSING_LABEL : fmtVehicleId(Number(value))}</strong></div>;
                })}
            </div>
        </section>
    );
}
