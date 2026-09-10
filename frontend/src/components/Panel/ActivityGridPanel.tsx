"use client";

import { useEffect, useState } from "react";
import { Grid3x3, X } from "lucide-react";
import { fetchActivityGridHex } from "@/services/api";
import { ActivityGridFeature } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import { classificationColor, classificationTier } from "@/constants/mapColors";
import { MISSING_LABEL, fmtFloatId, fmtIntId } from "@/utils/format";

const TOTAL_HEXES = 378;
const INPUT_LABELS: Record<string, string> = { norm_volume: "Volume kendaraan", norm_poi: "Jumlah POI", norm_penduduk: "Jumlah penduduk" };

export default function ActivityGridPanel({ hexId, onClose }: { hexId: number | null; onClose: () => void }) {
    if (hexId == null) return null;
    return <ActivityGridDetail key={hexId} hexId={hexId} onClose={onClose} />;
}

function ActivityGridDetail({ hexId, onClose }: { hexId: number; onClose: () => void }) {
    const [feature, setFeature] = useState<ActivityGridFeature | null>(null);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let mounted = true;
        fetchActivityGridHex(hexId)
            .then((value) => mounted && setFeature(value))
            .catch((err) => mounted && setError(err instanceof Error ? err : new Error("Data grid tidak tersedia")));
        return () => {
            mounted = false;
        };
    }, [hexId]);

    const props = feature?.properties;
    const tier = classificationTier(props?.klasifikasi_potensi);
    const badgeColor = classificationColor(props?.klasifikasi_potensi);
    const badgeText = tier >= 4 ? "#ffffff" : "#0f172a";

    return (
        <aside className="monitoring-panel segment-panel">
            <div className="panel-header">
                <div className="panel-location-icon"><Grid3x3 aria-hidden="true" /></div>
                <div className="panel-title">
                    <span>GRID POTENSI AKTIVITAS</span>
                    <h2>Hex {hexId}</h2>
                </div>
                <button onClick={onClose} className="panel-close" aria-label="Tutup panel grid"><X aria-hidden="true" /></button>
            </div>
            <div className="panel-content">
                {!props && !error && <div className="segment-overview"><Skeleton height={16} width="62%" /><Skeleton height={14} width="28%" /></div>}
                {error && <div className="segment-state error-state"><strong>Data grid tidak tersedia</strong><span>{error.message}</span></div>}
                {props && (
                    <>
                        <div className="segment-overview">
                            <strong>{props.klasifikasi_potensi}</strong>
                            <span>Peringkat {fmtIntId(props.ranking)} dari {TOTAL_HEXES}</span>
                            <b className="priority-badge" style={{ background: badgeColor, color: badgeText }}>{props.klasifikasi_potensi}</b>
                        </div>
                        <section className="panel-section segment-decision-section">
                            <SectionTitle title="Skor potensi AHP" meta={`Versi ${props.ahp_weight_version}`} />
                            <div className="segment-score"><span>SKOR TOTAL AHP</span><strong>{fmtFloatId(props.skor_total_ahp, 2)}</strong></div>
                        </section>
                        <section className="panel-section">
                            <SectionTitle title="Input ternormalisasi" meta="Skala 1–100 (dari model Excel)" />
                            {Object.entries(INPUT_LABELS).map(([key, label]) => {
                                const value = Number(props[key as keyof typeof props] ?? 0);
                                const width = Math.max(0, Math.min(100, value));
                                return (
                                    <div className="criterion-card" key={key}>
                                        <div className="criterion-card-header"><span>{label}</span><strong>{fmtFloatId(value, 2)}</strong></div>
                                        <div aria-hidden="true" style={{ height: 6, borderRadius: 3, background: "#e2e8f0", marginTop: 6 }}>
                                            <div style={{ width: `${width}%`, height: "100%", borderRadius: 3, background: classificationColor(props.klasifikasi_potensi) }} />
                                        </div>
                                    </div>
                                );
                            })}
                        </section>
                        <section className="panel-section">
                            <SectionTitle title="Data mentah" meta="Sumber: model offline" />
                            <div className="criteria-grid">
                                <div className="criteria-item"><span>POI total</span><strong>{fmtIntId(props.poi_total)}</strong></div>
                                <div className="criteria-item"><span>Penduduk</span><strong>{fmtIntId(props.penduduk)}</strong></div>
                                <div className="criteria-item"><span>Volume (mean)</span><strong>{fmtFloatId(props.volume_mean, 1)}</strong></div>
                                <div className="criteria-item"><span>Luas</span><strong>{fmtFloatId(props.luas_km2, 3)} km²</strong></div>
                            </div>
                            <div className="normalized-values">
                                <span className="subsection-label">RINCIAN POI</span>
                                <div className="criteria-grid">
                                    {Object.entries(props.poi_breakdown ?? {}).map(([category, count]) => (
                                        <div className="criteria-item" key={category}><span>{category}</span><strong>{count === null ? MISSING_LABEL : fmtIntId(count)}</strong></div>
                                    ))}
                                </div>
                            </div>
                        </section>
                    </>
                )}
            </div>
        </aside>
    );
}
