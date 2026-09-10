"use client";

import { useEffect, useState } from "react";
import { Bus, X } from "lucide-react";
import { fetchBusStopDetail } from "@/services/api";
import { BusStopDetail } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import { classificationColor, classificationTier } from "@/constants/mapColors";
import { MISSING_LABEL, fmtDateTimeId, fmtFloatId, fmtIntId } from "@/utils/format";

const COMPONENTS: { key: keyof BusStopDetail; label: string }[] = [
    { key: "accessibility_score", label: "Aksesibilitas (POI 500 m)" },
    { key: "facility_score", label: "Fasilitas (survei)" },
    { key: "environment_score", label: "Lingkungan (survei)" },
];

export default function BusStopPanel({ sourceId, onClose }: { sourceId: string | null; onClose: () => void }) {
    if (!sourceId) return null;
    return <BusStopDetailPanel key={sourceId} sourceId={sourceId} onClose={onClose} />;
}

function BusStopDetailPanel({ sourceId, onClose }: { sourceId: string; onClose: () => void }) {
    const [detail, setDetail] = useState<BusStopDetail | null>(null);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let mounted = true;
        fetchBusStopDetail(sourceId)
            .then((value) => mounted && setDetail(value))
            .catch((err) => mounted && setError(err instanceof Error ? err : new Error("Data halte tidak tersedia")));
        return () => {
            mounted = false;
        };
    }, [sourceId]);

    const tier = classificationTier(detail?.intervention_class);
    const badgeColor = classificationColor(detail?.intervention_class);
    const badgeText = tier >= 4 ? "#ffffff" : "#0f172a";
    const photos = (detail?.media ?? []).filter((item) => item?.url);

    return (
        <aside className="monitoring-panel segment-panel">
            <div className="panel-header">
                <div className="panel-location-icon"><Bus aria-hidden="true" /></div>
                <div className="panel-title">
                    <span>HALTE SURVEI</span>
                    <h2>{detail?.title ?? sourceId}</h2>
                </div>
                <button onClick={onClose} className="panel-close" aria-label="Tutup panel halte"><X aria-hidden="true" /></button>
            </div>
            <div className="panel-content">
                {!detail && !error && <div className="segment-overview"><Skeleton height={16} width="62%" /><Skeleton height={14} width="28%" /></div>}
                {error && <div className="segment-state error-state"><strong>Data halte tidak tersedia</strong><span>{error.message}</span></div>}
                {detail && (
                    <>
                        <div className="segment-overview">
                            <strong>{detail.intervention_class ?? "Belum dinilai"}</strong>
                            <span>{detail.intervention_rank == null ? "Peringkat belum tersedia" : `Peringkat intervensi ${fmtIntId(detail.intervention_rank)}`}</span>
                            <b className="priority-badge" style={{ background: badgeColor, color: badgeText }}>{detail.intervention_class ?? "—"}</b>
                        </div>
                        <section className="panel-section">
                            <SectionTitle title="Skor komponen" meta={`Skor intervensi ${detail.intervention_score == null ? MISSING_LABEL : fmtFloatId(detail.intervention_score, 3)}`} />
                            <div className="stat-grid">
                                {COMPONENTS.map(({ key, label }) => {
                                    const value = detail[key] as number | null;
                                    return (
                                        <div className="stat-card" key={key}>
                                            <span className="stat-label">{label}</span>
                                            <strong className={`stat-value${value == null ? " data-missing" : ""}`}>{value == null ? MISSING_LABEL : fmtFloatId(value, 2)}</strong>
                                        </div>
                                    );
                                })}
                            </div>
                        </section>
                        <section className="panel-section">
                            <SectionTitle title="POI sekitar" meta={`Dalam ${fmtIntId(detail.accessibility_buffer_m)} m`} />
                            {detail.accessibility_breakdown.length === 0 && <p className="data-empty">Tidak ada POI tercatat di sekitar halte</p>}
                            {detail.accessibility_breakdown.length > 0 && (
                                <div className="criteria-grid">
                                    {detail.accessibility_breakdown.map((item) => (
                                        <div className="criteria-item" key={item.category}><span>{item.category ?? "Tidak diketahui"}</span><strong>{fmtIntId(item.count)}</strong></div>
                                    ))}
                                </div>
                            )}
                        </section>
                        <section className="panel-section">
                            <SectionTitle title="Observasi" meta={detail.observed_at ? fmtDateTimeId(detail.observed_at) : MISSING_LABEL} />
                            {detail.observer_name && <p className="segment-note">Pengamat: {detail.observer_name}</p>}
                            {detail.description && <p className="segment-note">{detail.description}</p>}
                            {!detail.description && !detail.observer_name && <p className="data-empty">{MISSING_LABEL}</p>}
                        </section>
                        {photos.length > 0 && (
                            <section className="panel-section">
                                <SectionTitle title="Foto" meta={`${photos.length} media`} />
                                <div className="criteria-grid">
                                    {photos.map((item, index) => (
                                        // eslint-disable-next-line @next/next/no-img-element
                                        <img key={index} src={item.url} alt={`${detail.title} ${index + 1}`} style={{ width: "100%", borderRadius: 8 }} />
                                    ))}
                                </div>
                            </section>
                        )}
                    </>
                )}
            </div>
        </aside>
    );
}
