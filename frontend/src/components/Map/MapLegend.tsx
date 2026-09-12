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
        <div className={`map-legend ${open ? "open" : ""}`} aria-label="Legenda peta">
            <button type="button" className="map-legend-toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
                <Info aria-hidden="true" />
                <span>Legenda · {modeLabel}</span>
                {open ? <ChevronDown aria-hidden="true" /> : <ChevronUp aria-hidden="true" />}
            </button>
            {open && (
                <div className="map-legend-body">
                    {mode === "traffic" && (
                        <>
                            <section className="map-legend-section">
                                <h3>Emisi segmen (g/jam)</h3>
                                <ul className="legend-swatches">{segmentBuckets.map((bucket) => <li key={bucket.label}><i style={{ background: bucket.color }} />{bucket.label}</li>)}</ul>
                            </section>
                            <section className="map-legend-section">
                                <h3>CCTV: emisi CO₂ (g/min)</h3>
                                <ul className="legend-swatches">
                                    <li><i style={{ background: CAMERA_TIER_COLORS.low }} />&lt; 500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.medium }} />500–1.500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.high }} />&gt; 1.500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.unavailable }} />Tanpa data</li>
                                    <li><i style={{ background: "#38bdf8" }} />Historis (REPLAY)</li>
                                </ul>
                                <p className="legend-note">{cameraFresh}/{cameraTotal} segar{cameraStale > 0 ? ` · ${cameraStale} basi` : ""}{cameraHistorical > 0 ? ` · ${cameraHistorical} historis` : ""}</p>
                            </section>
                            <section className="map-legend-section">
                                <h3>Kesegaran data</h3>
                                <ul className="legend-swatches">
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
                            <section className="map-legend-section">
                                <h3>Potensi aktivitas (skor AHP)</h3>
                                <div className="legend-gradient">
                                    <div className="legend-gradient-bar" style={{ background: activityGradientCss() }} />
                                    {activityLabels
                                        ? <div className="legend-gradient-labels">{activityLabels.map((label) => <span key={label}>{label}</span>)}</div>
                                        : <div className="legend-gradient-labels"><span>Sangat Rendah</span><span>Sangat Tinggi</span></div>}
                                </div>
                                <ul className="legend-swatches"><li><i style={{ background: FIVE_TIER_COLORS.unknown }} />Tanpa data</li></ul>
                                <p className="legend-note">Skala warna mengikuti sebaran skor di layar. Hexagon mengikuti zoom.</p>
                            </section>
                            <section className="map-legend-section">
                                <h3>Kondisi halte (skor intervensi)</h3>
                                <div className="legend-gradient">
                                    <div className="legend-gradient-bar" style={{ background: interventionGradientCss() }} />
                                    <div className="legend-gradient-labels"><span>Prioritas</span><span>Baik</span></div>
                                </div>
                                <p className="legend-note">Skor rendah = prioritas intervensi. Klik halte untuk radius 500 m.</p>
                            </section>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
