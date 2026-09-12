"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";
import { CAMERA_TIER_COLORS, FRESHNESS_COLORS, FIVE_TIER_COLORS, activityGradientCss, interventionGradientCss, MAP_MODES, type MapMode } from "@/constants/mapColors";
import { formatNumber } from "@/utils/format";

interface MapLegendProps {
    mode: MapMode;
    segmentBuckets: { color: string; label: string }[];
    cameraFresh: number;
    cameraStale: number;
    cameraHistorical?: number;
    cameraTotal: number;
    activityBreaks?: number[] | null;
}

export default function MapLegend({ mode, segmentBuckets, cameraFresh, cameraStale, cameraHistorical = 0, cameraTotal, activityBreaks }: MapLegendProps) {
    const [open, setOpen] = useState(true);
    const modeLabel = MAP_MODES.find((item) => item.key === mode)?.label ?? "";
    const activityLabels = activityBreaks && activityBreaks.length >= 2
        ? activityBreaks.map((value) => formatNumber(value, Math.abs(value) >= 10 ? 0 : 1))
        : null;

    return (
        <div className={`absolute bottom-[14px] left-[14px] z-10 flex max-h-[calc(100%-160px)] w-[230px] flex-col rounded-lg border border-[rgba(148,163,184,0.23)] bg-[rgba(7,20,34,0.92)] text-[10px] text-[#dce7f3] shadow-[0_8px_24px_rgba(0,0,0,0.28)] backdrop-blur-[8px] max-[760px]:right-2 max-[760px]:bottom-2 max-[760px]:left-2 max-[760px]:max-h-[42vh] ${open ? "" : "max-[760px]:right-auto max-[760px]:w-[200px]"}`} aria-label="Legenda peta">
            <button type="button" className="flex w-full cursor-pointer items-center gap-2 rounded-lg border-0 bg-transparent px-[11px] py-[9px] text-left text-[10px] font-bold text-[#dce7f3] hover:bg-[#102238] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--green)] [&>svg]:h-3.5 [&>svg]:w-3.5 [&>svg]:flex-[0_0_14px] [&>span]:flex-1" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
                <Info aria-hidden="true" />
                <span>Legenda · {modeLabel}</span>
                {open ? <ChevronDown aria-hidden="true" /> : <ChevronUp aria-hidden="true" />}
            </button>
            {open && (
                <div className="flex flex-col gap-[10px] overflow-y-auto px-[11px] pt-1 pb-[10px] [&_h3]:my-[6px_0_5px] [&_h3]:text-[8px] [&_h3]:font-extrabold [&_h3]:tracking-[0.12em] [&_h3]:text-[#8ba0b8] [&_h3]:uppercase">
                    {mode === "traffic" && (
                        <>
                            <section>
                                <h3>Emisi segmen (g/jam)</h3>
                                <ul className="m-0 flex list-none flex-col gap-1 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-1.5 [&_li]:text-[9px] [&_li]:text-[var(--secondary)] [&_i]:h-[9px] [&_i]:w-[9px] [&_i]:flex-[0_0_9px] [&_i]:rounded-[3px]">{segmentBuckets.map((bucket) => <li key={bucket.label}><i style={{ background: bucket.color }} />{bucket.label}</li>)}</ul>
                            </section>
                            <section>
                                <h3>CCTV: emisi CO₂ (g/min)</h3>
                                <ul className="m-0 flex list-none flex-col gap-1 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-1.5 [&_li]:text-[9px] [&_li]:text-[var(--secondary)] [&_i]:h-[9px] [&_i]:w-[9px] [&_i]:flex-[0_0_9px] [&_i]:rounded-[3px]">
                                    <li><i style={{ background: CAMERA_TIER_COLORS.low }} />&lt; 500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.medium }} />500–1.500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.high }} />&gt; 1.500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.unavailable }} />Tanpa data</li>
                                    <li><i style={{ background: "#38bdf8" }} />Historis (REPLAY)</li>
                                </ul>
                                <p className="mt-[5px] mb-0 text-[8px] text-[var(--muted)]">{cameraFresh}/{cameraTotal} segar{cameraStale > 0 ? ` · ${cameraStale} basi` : ""}{cameraHistorical > 0 ? ` · ${cameraHistorical} historis` : ""}</p>
                            </section>
                            <section>
                                <h3>Kesegaran data</h3>
                                <ul className="m-0 flex list-none flex-col gap-1 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-1.5 [&_li]:text-[9px] [&_li]:text-[var(--secondary)] [&_i]:h-[9px] [&_i]:w-[9px] [&_i]:flex-[0_0_9px] [&_i]:rounded-[3px]">
                                    <li><i style={{ background: FRESHNESS_COLORS.fresh }} />Segar</li>
                                    <li><i style={{ background: FRESHNESS_COLORS.aging }} />Menua</li>
                                    <li><i style={{ background: FRESHNESS_COLORS.stale }} />Basi</li>
                                    <li><i style={{ background: FRESHNESS_COLORS.unknown }} />Tidak diketahui</li>
                                </ul>
                            </section>
                        </>
                    )}
                    {mode === "potential" && (
                        <>
                            <section>
                                <h3>Potensi aktivitas (skor AHP)</h3>
                                <div className="flex flex-col gap-1">
                                    <div className="h-[10px] rounded-[3px]" style={{ background: activityGradientCss() }} />
                                    {activityLabels
                                        ? <div className="flex justify-between text-[8px] text-[var(--muted)]">{activityLabels.map((label) => <span key={label}>{label}</span>)}</div>
                                        : <div className="flex justify-between text-[8px] text-[var(--muted)]"><span>Sangat Rendah</span><span>Sangat Tinggi</span></div>}
                                </div>
                                <ul className="m-0 flex list-none flex-col gap-1 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-1.5 [&_li]:text-[9px] [&_li]:text-[var(--secondary)] [&_i]:h-[9px] [&_i]:w-[9px] [&_i]:flex-[0_0_9px] [&_i]:rounded-[3px]"><li><i style={{ background: FIVE_TIER_COLORS.unknown }} />Tanpa data</li></ul>
                                <p className="mt-[5px] mb-0 text-[8px] text-[var(--muted)]">Skala warna mengikuti sebaran skor di layar. Hexagon mengikuti zoom.</p>
                            </section>
                            <section>
                                <h3>Kondisi halte (skor intervensi)</h3>
                                <div className="flex flex-col gap-1">
                                    <div className="h-[10px] rounded-[3px]" style={{ background: interventionGradientCss() }} />
                                    <div className="flex justify-between text-[8px] text-[var(--muted)]"><span>Prioritas</span><span>Baik</span></div>
                                </div>
                                <p className="mt-[5px] mb-0 text-[8px] text-[var(--muted)]">Skor rendah = prioritas intervensi. Klik halte untuk radius 500 m.</p>
                            </section>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
