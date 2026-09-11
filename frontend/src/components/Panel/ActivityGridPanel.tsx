"use client";

import { useEffect, useState } from "react";
import { Grid3x3, X } from "lucide-react";
import { fetchActivityGridHex } from "@/services/api";
import { ActivityGridFeature, ActivityGridHourPoint } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import { MISSING_LABEL, fmtFloatId, fmtIntId } from "@/utils/format";
import { useActivityGridHexHourly } from "@/hooks/useActivityGrid";
import ActivityPotentialCard from "./ActivityPotentialCard";

export default function ActivityGridPanel({ hexId, hour, onSelectHour, onClose }: {
    hexId: number | null;
    hour?: string | null;
    onSelectHour?: (hour: string) => void;
    onClose: () => void;
}) {
    if (hexId == null) return null;
    return <ActivityGridSeries key={hexId} hexId={hexId} hour={hour} onSelectHour={onSelectHour} onClose={onClose} />;
}

// Kept separate so the 24h series survives hourly scrubbing (the detail below
// remounts per hour via its key, this wrapper does not).
function ActivityGridSeries({ hexId, hour, onSelectHour, onClose }: {
    hexId: number;
    hour?: string | null;
    onSelectHour?: (hour: string) => void;
    onClose: () => void;
}) {
    const series = useActivityGridHexHourly(hexId);
    return <ActivityGridDetail key={`${hexId}-${hour ?? "static"}`} hexId={hexId} hour={hour ?? null} series={series} onSelectHour={onSelectHour} onClose={onClose} />;
}

function hourLabel(hour: string): string {
    return new Date(hour).toLocaleTimeString("id-ID", { hour: "2-digit" });
}

function HourPatternChart({ series, activeHour, onSelectHour }: {
    series: ActivityGridHourPoint[];
    activeHour: string | null;
    onSelectHour?: (hour: string) => void;
}) {
    if (series.length < 2) return null;
    const max = Math.max(...series.map((point) => point.skor_total_ahp ?? 0), 1);
    return (
        <section className="panel-section">
            <SectionTitle title="Pola 24 jam" meta={`${series.length} jam tersedia`} />
            <div className="activity-hour-chart">
                {series.map((point) => {
                    const active = point.hour === activeHour;
                    const score = point.skor_total_ahp;
                    const height = score == null ? 4 : Math.max(4, Math.round((score / max) * 100));
                    const label = hourLabel(point.hour);
                    return (
                        <button
                            type="button"
                            key={point.hour}
                            className={active ? "active" : ""}
                            onClick={() => onSelectHour?.(point.hour)}
                            title={`Pukul ${label} · ${score == null ? "tanpa data" : fmtFloatId(score, 1)}`}
                            aria-label={`Pukul ${label}${score == null ? ", tanpa data" : `, skor ${fmtFloatId(score, 1)}`}`}
                        >
                            <i data-empty={score == null || undefined} style={{ height: `${height}%` }} />
                        </button>
                    );
                })}
            </div>
            <div className="activity-hour-axis" aria-hidden="true">
                {series.map((point, index) => <span key={point.hour}>{index % 6 === 0 ? hourLabel(point.hour) : ""}</span>)}
            </div>
        </section>
    );
}

function ActivityGridDetail({ hexId, hour, series, onSelectHour, onClose }: {
    hexId: number;
    hour: string | null;
    series: ActivityGridHourPoint[];
    onSelectHour?: (hour: string) => void;
    onClose: () => void;
}) {
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
    const currentHourLabel = hour ? new Date(hour).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }) : null;
    const sourceMeta = !hour
        ? "Sumber: model offline"
        : props?.data_status === "no_data" ? `Pukul ${currentHourLabel} · tanpa data` : `Skor pukul ${currentHourLabel} · live`;

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
                        <HourPatternChart series={series} activeHour={hour} onSelectHour={onSelectHour} />
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
