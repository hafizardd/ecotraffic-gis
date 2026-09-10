"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";
import { CAMERA_TIER_COLORS, FRESHNESS_COLORS, SPATIAL_COLORS, FIVE_TIER_COLORS, FIVE_TIER_LEGEND, LAYER_LABELS, MapLayerKey } from "@/constants/mapColors";
import Checkbox from "@/components/ui/Checkbox";

interface MapLegendProps {
    visible: Record<MapLayerKey, boolean>;
    onToggle: (key: MapLayerKey) => void;
    segmentBuckets: { color: string; label: string }[];
    cameraFresh: number;
    cameraStale: number;
    cameraTotal: number;
}

const LAYER_KEYS = Object.keys(LAYER_LABELS) as MapLayerKey[];
const LAYER_DOT: Record<MapLayerKey, string> = {
    cameras: CAMERA_TIER_COLORS.low,
    segments: "#facc15",
    surveyStops: SPATIAL_COLORS.surveyStop,
    activityGrid: FIVE_TIER_COLORS.high,
};

export default function MapLegend({ visible, onToggle, segmentBuckets, cameraFresh, cameraStale, cameraTotal }: MapLegendProps) {
    const [open, setOpen] = useState(true);

    return (
        <div className={`map-legend ${open ? "open" : ""}`} aria-label="Legenda dan kontrol lapisan">
            <button type="button" className="map-legend-toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
                <Info aria-hidden="true" />
                <span>Legenda & Lapisan</span>
                {open ? <ChevronDown aria-hidden="true" /> : <ChevronUp aria-hidden="true" />}
            </button>
            {open && (
                <div className="map-legend-body">
                    <section className="map-legend-section">
                        <h3>Emisi segmen (g/jam)</h3>
                        <ul className="legend-swatches">{segmentBuckets.map((bucket) => <li key={bucket.label}><i style={{ background: bucket.color }} />{bucket.label}</li>)}</ul>
                    </section>
                    <section className="map-legend-section">
                        <h3>CCTV — emisi CO₂ (g/min)</h3>
                        <ul className="legend-swatches">
                            <li><i style={{ background: CAMERA_TIER_COLORS.low }} />&lt; 500</li>
                            <li><i style={{ background: CAMERA_TIER_COLORS.medium }} />500–1.500</li>
                            <li><i style={{ background: CAMERA_TIER_COLORS.high }} />&gt; 1.500</li>
                            <li><i style={{ background: CAMERA_TIER_COLORS.unavailable }} />Tanpa data</li>
                        </ul>
                        <p className="legend-note">{cameraFresh}/{cameraTotal} segar{cameraStale > 0 ? ` · ${cameraStale} basi` : ""}</p>
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
                    <section className="map-legend-section">
                        <h3>Potensi aktivitas & prioritas halte</h3>
                        <ul className="legend-swatches">{FIVE_TIER_LEGEND.map((tier) => <li key={tier.label}><i style={{ background: tier.color }} />{tier.label}</li>)}</ul>
                    </section>
                    <section className="map-legend-section">
                        <h3>Lapisan</h3>
                        <ul className="legend-layers">
                            {LAYER_KEYS.map((key) => (
                                <li key={key}>
                                    <Checkbox className={visible[key] ? "active" : ""} checked={visible[key]} onChange={() => onToggle(key)}
                                        label={<><i style={{ background: LAYER_DOT[key] }} />{LAYER_LABELS[key]}</>} />
                                </li>
                            ))}
                        </ul>
                    </section>
                </div>
            )}
        </div>
    );
}
