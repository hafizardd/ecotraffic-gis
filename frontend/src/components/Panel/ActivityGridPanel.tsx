"use client";

import { useEffect, useState } from "react";
import { Grid3x3, X } from "lucide-react";
import { fetchActivityGridHex } from "@/services/api";
import { ActivityGridFeature } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import { MISSING_LABEL, fmtFloatId, fmtIntId } from "@/utils/format";
import ActivityPotentialCard from "./ActivityPotentialCard";

export default function ActivityGridPanel({ hexId, hour, onClose }: { hexId: number | null; hour?: string | null; onClose: () => void }) {
    if (hexId == null) return null;
    return <ActivityGridDetail key={`${hexId}-${hour ?? "static"}`} hexId={hexId} hour={hour ?? null} onClose={onClose} />;
}

function ActivityGridDetail({ hexId, hour, onClose }: { hexId: number; hour: string | null; onClose: () => void }) {
    const [feature, setFeature] = useState<ActivityGridFeature | null>(null);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let mounted = true;
        fetchActivityGridHex(hexId, hour)
            .then((value) => mounted && setFeature(value))
            .catch((err) => mounted && setError(err instanceof Error ? err : new Error("Data grid tidak tersedia")));
        return () => {
            mounted = false;
        };
    }, [hexId, hour]);

    const props = feature?.properties;
    const hourLabel = hour ? new Date(hour).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }) : null;
    const sourceMeta = !hour
        ? "Sumber: model offline"
        : props?.data_status === "no_data" ? `Pukul ${hourLabel} · tanpa data` : `Skor pukul ${hourLabel} · live`;

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
                        <ActivityPotentialCard properties={props} />
                        <section className="panel-section">
                            <SectionTitle title="Data mentah" meta={sourceMeta} />
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
