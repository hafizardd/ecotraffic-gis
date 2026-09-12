"use client";

import { useEffect, useState } from "react";
import { Grid3x3, X } from "lucide-react";
import { fetchActivityGridHex } from "@/services/api";
import { ActivityGridFeature } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import { MISSING_LABEL, fmtFloatId, fmtIntId, formatCameraName } from "@/utils/format";
import { dataStatusLabel, noDataReasonLabel } from "@/utils/activityGrid";
import ActivityPotentialCard from "./ActivityPotentialCard";
import AutoInsightCard from "./AutoInsightCard";
import { CRITERIA_GRID_CLASS, PANEL_CLASS, PANEL_CLOSE_CLASS, PANEL_ICON_CLASS, SEGMENT_OVERVIEW_CLASS, SEGMENT_PANEL_CONTENT_CLASS, SEGMENT_PANEL_HEADER_CLASS, SEGMENT_PANEL_TITLE_CLASS, SEGMENT_SECTION_CLASS, SEGMENT_STATE_CLASS } from "@/styles/tailwind";

export default function ActivityGridPanel({ hexId, hour, onClose }: {
    hexId: number | null;
    hour?: string | null;
    onClose: () => void;
}) {
    if (hexId == null) return null;
    return <ActivityGridDetail key={`${hexId}-${hour ?? "static"}`} hexId={hexId} hour={hour ?? null} onClose={onClose} />;
}

function ActivityGridDetail({ hexId, hour, onClose }: {
    hexId: number;
    hour: string | null;
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
        ? "Sumber: data statis"
        : props?.data_status === "no_data" ? `Pukul ${currentHourLabel} · tanpa data`
            : props?.data_status === "fallback" ? `Pukul ${currentHourLabel} · perkiraan area terdekat`
                : `Skor pukul ${currentHourLabel} · terukur`;

    return (
        <aside className={PANEL_CLASS} aria-label={`Detail grid potensi Hex ${hexId}`}>
            <div className={SEGMENT_PANEL_HEADER_CLASS}>
                <div className={`${PANEL_ICON_CLASS} flex-[0_0_auto]`}><Grid3x3 aria-hidden="true" /></div>
                <div className={SEGMENT_PANEL_TITLE_CLASS}>
                    <span>Grid potensi aktivitas</span>
                    <h2>Sel {hexId}</h2>
                </div>
                <button onClick={onClose} className={PANEL_CLOSE_CLASS} aria-label="Tutup panel grid"><X aria-hidden="true" /></button>
            </div>
            <div className={SEGMENT_PANEL_CONTENT_CLASS}>
                {!props && !error && <div className={SEGMENT_OVERVIEW_CLASS}><Skeleton height={16} width="62%" /><Skeleton height={14} width="28%" /></div>}
                {error && <div className={`${SEGMENT_STATE_CLASS} [&>strong]:text-[#fca5a5]`} role="alert"><strong>Data grid tidak tersedia</strong><span>{error.message}</span></div>}
                {props && (
                    <>
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
