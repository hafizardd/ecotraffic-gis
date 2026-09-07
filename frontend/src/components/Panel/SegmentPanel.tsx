"use client";

import { useEffect, useState } from "react";
import { Route, X } from "lucide-react";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchSegmentEmission } from "@/services/api";
import { SegmentEmissionDetail } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";

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
    const { segmentMap, connectionStatus } = useEmissionsContext();

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
    const liveDetail = detail && update ? { ...detail, ...update, pollutant_totals_g_h: update.pollutant_totals ?? detail.pollutant_totals_g_h, volume_per_hour: update.volume_per_hour ?? detail.volume_per_hour } : detail;

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
                {liveDetail && <><div className="segment-state">Sumber: {connectionStatus === "connected" ? "Realtime" : "Terakhir diterima"}{liveDetail.freshness_status ? ` · Data: ${liveDetail.freshness_status}` : ""}{!liveDetail.calculated_at && " · Belum ada perhitungan emisi"}</div><SegmentDetails detail={liveDetail} /></>}
            </div>
        </aside>
    );
}

function SegmentDetails({ detail }: { detail: SegmentEmissionDetail }) {
    return (
        <>
            <div className="segment-overview">
                <strong>{detail.road_segment_id}</strong>
                <span>{detail.length_km.toFixed(2)} km</span>
                <b className={`priority-badge priority-${detail.priority ?? "unknown"}`}>
                    {detail.priority ?? "Tidak tersedia"}
                </b>
            </div>
            <section className="panel-section">
                <div className="section-heading"><div><span>EMISI SEGMEN</span><small>Nilai agregat dalam g/jam</small></div></div>
                <div className="stat-grid">
                    {EMISSION_DEFINITIONS.map(({ key, label }) => (
                        <div className={`stat-card pollutant-${key}`} key={key}>
                            <span className="stat-label"><i className="pollutant-dot" />{label}</span>
                            <strong className="stat-value">{detail.pollutant_totals_g_h?.[key] == null ? "N/A" : Number(detail.pollutant_totals_g_h[key]).toFixed(2)}<small>g/hr</small></strong>
                        </div>
                    ))}
                </div>
            </section>
            <section className="panel-section">
                <div className="segment-score"><span>DECISION SCORE</span><strong>{detail.decision_score == null ? "Tidak tersedia" : detail.decision_score.toFixed(3)}</strong></div>
                <p className="criteria-status">Kriteria spasial: {detail.spatial_criteria_status}</p>
                <div className="criteria-grid">{Object.entries(detail.raw_criteria ?? {}).map(([key, value]) => <div key={key}><span>{key}</span><strong>{value == null ? "N/A" : String(value)}</strong></div>)}</div>
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
    const formatPopulation = (value: number | null | undefined) => value == null ? "Data tidak tersedia" : `${value.toLocaleString("id-ID")} jiwa`;
    return (
        <section className="panel-section">
            <div className="section-heading"><div><span>POPULASI WILAYAH</span><small>Konteks administratif segmen</small></div></div>
            {!primary && intersecting.length === 0 && <p className="data-empty">Data tidak tersedia</p>}
            {primary && (
                <>
                    <p><strong>Kecamatan:</strong> {primary.district_name ?? "Data tidak tersedia"}</p>
                    <p><strong>Populasi wilayah:</strong> {formatPopulation(primary.population)}</p>
                    <p><strong>Metode:</strong> {primary.method ?? "Data tidak tersedia"}</p>
                </>
            )}
            {intersecting.length > 0 && (
                <details>
                    <summary>Wilayah berbatasan ({intersecting.length})</summary>
                    {intersecting.map((zone, index) => (
                        <p key={index}><strong>{zone.district_name}:</strong> {formatPopulation(zone.population)} — {zone.overlap_share == null ? "N/A" : `${(zone.overlap_share * 100).toFixed(0)}%`} tumpang tindih</p>
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
            <p><strong>K3 — Akses Halte:</strong> {rawCriteria["K3"] == null ? "Data tidak tersedia" : Number(rawCriteria["K3"]).toFixed(3)}</p>
            <p className="indent">Survei terdekat: {k3?.nearby_observation_count ?? "Data tidak tersedia"} · Skor halte: {k3?.composite_stop_score == null ? "N/A" : Number(k3.composite_stop_score).toFixed(2)} · Versi: {k3?.scoring_version ?? "N/A"}</p>
            <p><strong>K4 — Aktivitas:</strong> {rawCriteria["K4"] == null ? "Data tidak tersedia" : Number(rawCriteria["K4"]).toFixed(3)}</p>
            <p className="indent">POI dalam buffer: {k4?.poi_count ?? "Data tidak tersedia"} · Berbobot: {k4?.weighted_poi_count ?? "N/A"} · Buffer: {k4?.buffer_distance_m ?? "N/A"} m</p>
            <p><strong>K5 — Populasi (est.):</strong> {rawCriteria["K5"] == null ? "Data tidak tersedia" : Number(rawCriteria["K5"]).toFixed(3)}</p>
            <p className="indent">{k5?.method ?? "Data tidak tersedia"} · Sumber tingkat kecamatan (perkiraan, bukan jumlah pasti di sepanjang jalan)</p>
            {normalized && (
                <div className="criteria-grid">{Object.entries(normalized).map(([key, value]) => <div key={key}><span>{key} (norm)</span><strong>{value == null ? "N/A" : Number(value).toFixed(3)}</strong></div>)}</div>
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
    return (
        <section className="panel-section">
            <div className="section-heading"><div><span>{title}</span><small>{subtitle}</small></div>{estimated && <b className="estimate-badge">Estimasi</b>}</div>
            {values == null && <p className="data-empty">{unavailableLabel}</p>}
            <div className="vehicle-summary">
                {VEHICLE_TYPES.map((key) => {
                    const value = values?.[key];
                    return <div key={key}><span>{key}</span><strong>{value == null ? "N/A" : Number(value).toFixed(1)}</strong></div>;
                })}
            </div>
        </section>
    );
}
