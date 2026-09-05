"use client";

import { useEffect, useState } from "react";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchSegmentEmission } from "@/services/api";
import { SegmentEmissionDetail } from "@/types";

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

    useEffect(() => {
        let mounted = true;
        fetchSegmentEmission(segmentId)
            .then((value) => mounted && setDetail(value))
            .catch((err) => mounted && setError(err instanceof Error ? err : new Error("Data segmen tidak tersedia")));
        return () => {
            mounted = false;
        };
    }, [segmentId]);

    return (
        <aside className="monitoring-panel segment-panel">
            <div className="panel-header">
                <div className="panel-location-icon">━</div>
                <div className="panel-title">
                    <span>SEGMEN TERPILIH</span>
                    <h2>{detail?.name ?? segmentId}</h2>
                </div>
                <button onClick={onClose} className="panel-close" aria-label="Tutup panel segmen">×</button>
            </div>
            <div className="panel-content">
                {!detail && !error && <div className="segment-state"><span className="loading-spinner" />Memuat detail segmen...</div>}
                {error && <div className="segment-state error-state"><strong>Data segmen tidak tersedia</strong><span>{error.message}</span></div>}
                {detail && <SegmentDetails detail={detail} />}
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
                            <strong className="stat-value">{detail.pollutant_totals_g_h[key] == null ? "N/A" : Number(detail.pollutant_totals_g_h[key]).toFixed(2)}<small>g/hr</small></strong>
                        </div>
                    ))}
                </div>
            </section>
            <section className="panel-section">
                <div className="segment-score"><span>DECISION SCORE</span><strong>{detail.decision_score == null ? "Tidak tersedia" : detail.decision_score.toFixed(3)}</strong></div>
                <p className="criteria-status">Kriteria spasial: {detail.spatial_criteria_status}</p>
                <div className="criteria-grid">{Object.entries(detail.raw_criteria).map(([key, value]) => <div key={key}><span>{key}</span><strong>{value == null ? "N/A" : String(value)}</strong></div>)}</div>
            </section>
            <VehicleMetrics title="VOLUME KENDARAAN" subtitle="Agregat per jam" values={detail.volume_per_hour} unavailableLabel="Volume belum tersedia dari snapshot occupancy" />
            <VehicleMetrics title="VKT" subtitle="Kendaraan-kilometer per jam" values={detail.vkt_km_h} unavailableLabel="VKT belum tersedia dari snapshot occupancy" />
        </>
    );
}

function VehicleMetrics({
    title,
    subtitle,
    values,
    unavailableLabel,
}: {
    title: string;
    subtitle: string;
    values: Record<string, number> | null;
    unavailableLabel: string;
}) {
    return (
        <section className="panel-section">
            <div className="section-heading"><div><span>{title}</span><small>{subtitle}</small></div></div>
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
