"use client";

import { useEffect, useState } from "react";
import { Grid3x3, X } from "lucide-react";
import { fetchActivityGridHex } from "@/services/api";
import { ActivityGridFeature, ActivityGridHourPoint } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import { MISSING_LABEL, fmtDateTimeId, fmtFloatId, fmtIntId, formatCameraName } from "@/utils/format";
import { useActivityGridHexHourly } from "@/hooks/useActivityGrid";
import { withDay, dataStatusLabel, noDataReasonLabel } from "@/utils/activityGrid";
import ActivityPotentialCard from "./ActivityPotentialCard";
import AutoInsightCard from "./AutoInsightCard";
import { CRITERIA_GRID_CLASS, PANEL_CLASS, PANEL_CLOSE_CLASS, PANEL_ICON_CLASS, SEGMENT_OVERVIEW_CLASS, SEGMENT_PANEL_CONTENT_CLASS, SEGMENT_PANEL_HEADER_CLASS, SEGMENT_PANEL_TITLE_CLASS, SEGMENT_SECTION_CLASS, SEGMENT_STATE_CLASS } from "@/styles/tailwind";
import SpatialProvenanceRail, { type ProvenanceItem } from "./SpatialProvenanceRail";

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
    return <ActivityGridDetail key={`${hexId}-${hour ?? "static"}`} hexId={hexId} hour={hour ?? null} series={series}
        referenceDay={hour ? hour.slice(0, 10) : null} onSelectHour={onSelectHour} onClose={onClose} />;
}

function hourLabel(hour: string): string {
    return new Date(hour).toLocaleTimeString("id-ID", { hour: "2-digit" });
}

function HourPatternChart({ series, activeHour, referenceDay, onSelectHour }: {
    series: ActivityGridHourPoint[];
    activeHour: string | null;
    referenceDay: string | null;
    onSelectHour?: (hour: string) => void;
}) {
    if (series.length < 2) return null;
    const max = Math.max(...series.map((point) => point.skor_total_ahp ?? 0), 1);
    return (
        <section className={SEGMENT_SECTION_CLASS}>
            <SectionTitle title="Pola 24 jam" meta={`${series.length} jam tersedia`} />
            <div className="flex h-[78px] items-end gap-0.5 border-b border-[var(--contour)] px-0.5 pt-2">
                {series.map((point) => {
                    // The series is the canonical profile; rewrite to the day the
                    // panel is showing so selection/highlight stay in sync.
                    const displayHour = withDay(point.hour, referenceDay);
                    const active = displayHour === activeHour;
                    const score = point.skor_total_ahp;
                    const height = score == null ? 4 : Math.max(4, Math.round((score / max) * 100));
                    const label = hourLabel(point.hour);
                    return (
                        <button
                            type="button"
                            key={point.hour}
                            className="group flex h-full flex-1 cursor-pointer items-end rounded-[3px_3px_0_0] border-0 bg-transparent p-0 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--selection)]"
                            onClick={() => onSelectHour?.(displayHour)}
                            title={`Pukul ${label} · ${score == null ? "tanpa data" : fmtFloatId(score, 1)}`}
                            aria-label={`Pukul ${label}${score == null ? ", tanpa data" : `, skor ${fmtFloatId(score, 1)}`}`}
                        >
                            <i className={`block min-h-0.5 w-full rounded-[3px_3px_0_0] transition-opacity duration-120 group-hover:opacity-100 ${score == null ? "bg-[var(--muted)] opacity-35" : active ? "bg-[var(--selection)] opacity-100" : "bg-[var(--green)] opacity-65"}`} style={{ height: `${height}%` }} />
                        </button>
                    );
                })}
            </div>
            <div className="mt-[3px] flex gap-0.5" aria-hidden="true">
                {series.map((point, index) => <span className="flex-1 text-center text-[8px] text-[var(--muted)] tabular-nums" key={point.hour}>{index % 6 === 0 ? hourLabel(point.hour) : ""}</span>)}
            </div>
        </section>
    );
}

function ActivityGridDetail({ hexId, hour, series, referenceDay, onSelectHour, onClose }: {
    hexId: number;
    hour: string | null;
    series: ActivityGridHourPoint[];
    referenceDay: string | null;
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
        : props?.data_status === "no_data" ? `Pukul ${currentHourLabel} · tanpa data`
            : props?.data_status === "fallback" ? `Pukul ${currentHourLabel} · perkiraan (sel terdekat)`
                : `Skor pukul ${currentHourLabel} · live`;
    const qualityItem: ProvenanceItem | null = !props?.data_status
        ? null
        : props.is_interpolated
            ? { label: "Kualitas", value: "Replay · interpolasi", tone: "replay" }
            : props.data_status === "fallback"
                ? { label: "Kualitas", value: props.fallback_from == null ? "Perkiraan sel terdekat" : `Perkiraan · Hex ${props.fallback_from}`, tone: "estimated" }
                : props.data_status === "live"
                    ? { label: "Kualitas", value: dataStatusLabel(props.data_status), tone: "live" }
                    : { label: "Kualitas", value: dataStatusLabel(props.data_status) };

    return (
        <aside className={PANEL_CLASS} aria-label={`Detail grid potensi Hex ${hexId}`}>
            <div className={SEGMENT_PANEL_HEADER_CLASS}>
                <div className={`${PANEL_ICON_CLASS} flex-[0_0_auto]`}><Grid3x3 aria-hidden="true" /></div>
                <div className={SEGMENT_PANEL_TITLE_CLASS}>
                    <span>Grid potensi aktivitas</span>
                    <h2>Hex {hexId}</h2>
                </div>
                <button onClick={onClose} className={PANEL_CLOSE_CLASS} aria-label="Tutup panel grid"><X aria-hidden="true" /></button>
            </div>
            <div className={SEGMENT_PANEL_CONTENT_CLASS}>
                {!props && !error && <div className={SEGMENT_OVERVIEW_CLASS}><Skeleton height={16} width="62%" /><Skeleton height={14} width="28%" /></div>}
                {error && <div className={`${SEGMENT_STATE_CLASS} [&>strong]:text-[#fca5a5]`} role="alert"><strong>Data grid tidak tersedia</strong><span>{error.message}</span></div>}
                {props && (
                    <>
                        <SpatialProvenanceRail items={[
                            { label: "Entitas", value: `Hex ${hexId}` },
                            props.source ? { label: "Sumber", value: props.source } : null,
                            hour ? { label: "Waktu", value: fmtDateTimeId(hour), title: hour } : null,
                            qualityItem,
                        ]} />
                        <ActivityPotentialCard properties={props} />
                        <AutoInsightCard entity={{ type: "hex", id: hexId }} label={`grid Hex ${hexId}`} />
                        <section className={SEGMENT_SECTION_CLASS}>
                            <SectionTitle title="Jejak sumber" meta={hour ? currentHourLabel ?? undefined : "Model offline"} />
                            <dl className="m-0 grid gap-2 text-[11px]">
                                <SourceRow label="Status" value={dataStatusLabel(props.data_status)} />
                                {props.is_interpolated && <SourceRow label="Metode" value="Interpolasi 24 jam; bukan pengamatan langsung" />}
                                {props.data_status === "fallback" && props.fallback_from != null && <SourceRow label="Rujukan" value={`Hex ${props.fallback_from} · tetangga terdekat`} />}
                                {noDataReasonLabel(props.no_data_reason) && <SourceRow label="Catatan" value={noDataReasonLabel(props.no_data_reason)!} />}
                                <SourceRow label="Segmen" value={props.source_segments?.length ? props.source_segments.join(", ") : "Tidak tercatat"} />
                                <SourceRow label="Kamera" value={props.source_cameras?.length ? props.source_cameras.map(formatCameraName).join(", ") : "Tidak tercatat"} />
                            </dl>
                        </section>
                        <HourPatternChart series={series} activeHour={hour} referenceDay={referenceDay} onSelectHour={onSelectHour} />
                        <section className={SEGMENT_SECTION_CLASS}>
                            <SectionTitle title="Data mentah" meta={sourceMeta} />
                            <div className={CRITERIA_GRID_CLASS}>
                                <div><span>POI total</span><strong>{fmtIntId(props.poi_total)}</strong></div>
                                <div><span>Penduduk</span><strong>{fmtIntId(props.penduduk)}</strong></div>
                                <div><span>Volume (mean)</span><strong>{fmtFloatId(props.volume_mean, 1)}</strong></div>
                                <div><span>Luas</span><strong>{fmtFloatId(props.luas_km2, 3)} km²</strong></div>
                            </div>
                            <div className="mt-[15px] border-t border-[rgba(148,163,184,0.09)] pt-[14px]">
                                <span className="mx-px mt-0 mb-[9px] block text-[9px] font-extrabold leading-[1.2] tracking-[0.09em] text-[#718198]">RINCIAN POI</span>
                                <div className={CRITERIA_GRID_CLASS}>
                                    {Object.entries(props.poi_breakdown ?? {}).map(([category, count]) => (
                                        <div key={category}><span>{category}</span><strong>{count === null ? MISSING_LABEL : fmtIntId(count)}</strong></div>
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

function SourceRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="grid min-w-0 grid-cols-[68px_minmax(0,1fr)] gap-3 border-b border-[var(--border)] pb-2 last:border-b-0 last:pb-0">
            <dt className="text-[var(--muted)]">{label}</dt>
            <dd className="m-0 min-w-0 text-[var(--secondary)] [overflow-wrap:anywhere]">{value}</dd>
        </div>
    );
}
