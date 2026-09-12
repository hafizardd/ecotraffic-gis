"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";
import { CAMERA_TIER_COLORS, FRESHNESS_COLORS, FIVE_TIER_COLORS, activityGradientCss, interventionGradientCss, MAP_MODES, type MapLayerKey, type MapMode } from "@/constants/mapColors";
import { formatNumber } from "@/utils/format";

interface MapLegendProps {
    mode: MapMode;
    segmentBuckets: { color: string; label: string }[];
    cameraFresh: number;
    cameraStale: number;
    cameraHistorical?: number;
    cameraTotal: number;
    activityBreaks?: number[] | null;
    layerVisibility: Record<MapLayerKey, boolean>;
}

export default function MapLegend({ mode, segmentBuckets, cameraFresh, cameraStale, cameraHistorical = 0, cameraTotal, activityBreaks, layerVisibility }: MapLegendProps) {
    const [open, setOpen] = useState(false);
    const modeLabel = MAP_MODES.find((item) => item.key === mode)?.label ?? "";
    const activityLabels = activityBreaks && activityBreaks.length >= 2
        ? activityBreaks.map((value) => formatNumber(value, Math.abs(value) >= 10 ? 0 : 1))
        : null;

    return (
        <aside className={`absolute left-3 z-[19] flex max-h-[calc(100%-156px)] flex-col overflow-hidden rounded-[var(--radius-md)] border border-[var(--contour-strong)] bg-[rgba(11,32,41,0.94)] text-[11px] text-[var(--text)] shadow-[var(--shadow-float)] backdrop-blur-[10px] max-[760px]:left-2 max-[760px]:max-h-[48vh] ${mode === "potential" ? "bottom-3 max-[760px]:bottom-[112px]" : "bottom-3 max-[760px]:bottom-2"} ${open ? "w-[248px] max-[760px]:right-2 max-[760px]:w-auto" : "w-auto max-w-[220px]"}`} aria-label="Legenda peta">
            <button type="button" className="flex min-h-10 w-full cursor-pointer items-center gap-2 border-0 bg-transparent px-3 text-left text-[11px] font-semibold text-[var(--text)] transition-colors hover:bg-[var(--surface)] [&>svg]:h-4 [&>svg]:w-4 [&>svg]:flex-[0_0_16px] [&>span]:flex-1" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-controls="map-legend-content">
                <Info className="text-[var(--selection)]" aria-hidden="true" />
                <span>Legenda · {modeLabel}</span>
                {open ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}
            </button>
            {open && (
                <div id="map-legend-content" className="flex flex-col gap-3 overflow-y-auto border-t border-[var(--border)] px-3 pt-2 pb-3 [&_h3]:my-[5px_0_7px] [&_h3]:text-[10px] [&_h3]:font-bold [&_h3]:tracking-[0.1em] [&_h3]:text-[var(--muted)] [&_h3]:uppercase">
                    {mode === "traffic" && (
                        <>
                            {layerVisibility.segments && <section>
                                <h3>Emisi segmen (g/jam)</h3>
                                <ul className="m-0 flex list-none flex-col gap-1.5 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-2 [&_li]:text-[11px] [&_li]:text-[var(--secondary)] [&_i]:h-2.5 [&_i]:w-2.5 [&_i]:flex-[0_0_10px] [&_i]:rounded-[var(--radius-badge)]">{segmentBuckets.map((bucket) => <li key={bucket.label}><i style={{ background: bucket.color }} />{bucket.label}</li>)}</ul>
                            </section>}
                            {layerVisibility.cameras && <><section>
                                <h3>CCTV: emisi CO₂ (g/min)</h3>
                                <ul className="m-0 flex list-none flex-col gap-1.5 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-2 [&_li]:text-[11px] [&_li]:text-[var(--secondary)] [&_i]:h-2.5 [&_i]:w-2.5 [&_i]:flex-[0_0_10px] [&_i]:rounded-[var(--radius-badge)]">
                                    <li><i style={{ background: CAMERA_TIER_COLORS.low }} />&lt; 500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.medium }} />500–1.500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.high }} />&gt; 1.500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.unavailable }} />Tanpa data</li>
                                    <li><i style={{ background: "#38bdf8" }} />Historis (REPLAY)</li>
                                </ul>
                                <p className="mt-2 mb-0 text-[10px] leading-4 text-[var(--muted)]">{cameraFresh}/{cameraTotal} segar{cameraStale > 0 ? ` · ${cameraStale} basi` : ""}{cameraHistorical > 0 ? ` · ${cameraHistorical} historis` : ""}</p>
                            </section>
                            <section>
                                <h3>Kesegaran data</h3>
                                <ul className="m-0 flex list-none flex-col gap-1.5 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-2 [&_li]:text-[11px] [&_li]:text-[var(--secondary)] [&_i]:h-2.5 [&_i]:w-2.5 [&_i]:flex-[0_0_10px] [&_i]:rounded-[var(--radius-badge)]">
                                    <li><i style={{ background: FRESHNESS_COLORS.fresh }} />Segar</li>
                                    <li><i style={{ background: FRESHNESS_COLORS.aging }} />Menua</li>
                                    <li><i style={{ background: FRESHNESS_COLORS.stale }} />Basi</li>
                                    <li><i style={{ background: FRESHNESS_COLORS.unknown }} />Tidak diketahui</li>
                                </ul>
                            </section>
                            </>}
                        </>
                    )}
                    {mode === "potential" && (
                        <>
                            {layerVisibility.activityGrid && <section>
                                <h3>Potensi aktivitas (skor AHP)</h3>
                                <div className="flex flex-col gap-1">
                                    <div className="h-2.5 rounded-[var(--radius-badge)]" style={{ background: activityGradientCss() }} />
                                    {activityLabels
                                        ? <div className="flex justify-between text-[10px] text-[var(--muted)]">{activityLabels.map((label) => <span key={label}>{label}</span>)}</div>
                                        : <div className="flex justify-between text-[10px] text-[var(--muted)]"><span>Sangat rendah</span><span>Sangat tinggi</span></div>}
                                </div>
                                <ul className="mt-2 mb-0 flex list-none flex-col gap-1 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-2 [&_li]:text-[11px] [&_li]:text-[var(--secondary)] [&_i]:h-2.5 [&_i]:w-2.5 [&_i]:flex-[0_0_10px] [&_i]:rounded-[var(--radius-badge)]"><li><i style={{ background: FIVE_TIER_COLORS.unknown }} />Tanpa data</li></ul>
                                <p className="mt-2 mb-0 text-[10px] leading-4 text-[var(--muted)]">Skala warna mengikuti sebaran skor di layar. Hexagon mengikuti zoom.</p>
                            </section>}
                            {layerVisibility.surveyStops && <section>
                                <h3>Kondisi halte (skor intervensi)</h3>
                                <div className="flex flex-col gap-1">
                                    <div className="h-2.5 rounded-[var(--radius-badge)]" style={{ background: interventionGradientCss() }} />
                                    <div className="flex justify-between text-[10px] text-[var(--muted)]"><span>Prioritas</span><span>Baik</span></div>
                                </div>
                                <p className="mt-2 mb-0 text-[10px] leading-4 text-[var(--muted)]">Skor rendah = prioritas intervensi. Klik halte untuk radius 500 m.</p>
                            </section>}
                        </>
                    )}
                </div>
            )}
        </aside>
    );
}
