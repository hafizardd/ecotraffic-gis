"use client";
import { useEffect, useRef, useState } from "react";
import Map, { MapRef, NavigationControl, Source, Layer } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import CameraMarker from "./CameraMarker";
import SidePanel from "../Panel/SidePanel";
import { getMarkerColor } from "@/utils/markerColor";
import useCameras from "@/hooks/useCameras";
import { CameraFeature } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";
import useSegments from "@/hooks/useSegments";
import SegmentPanel from "../Panel/SegmentPanel";

export default function MapView() {
    const { cameras, loading, error } = useCameras();
    const { emissionMap, segmentMap } = useEmissionsContext();
    const { segments } = useSegments();
    const [selectedCamera, setSelectedCamera] = useState<CameraFeature | null>(null);
    const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
    const [hoveredSegmentId, setHoveredSegmentId] = useState<string | null>(null);
    const [style, setStyle] = useState<"street-2d-building" | "dark">("street-2d-building");
    const [layerMode, setLayerMode] = useState<"all" | "cameras" | "segments">("all");
    const isDark = style === "dark";
    const mapRef = useRef<MapRef>(null);
    const mapAreaRef = useRef<HTMLDivElement>(null);
    const geoMapidApiKey = process.env.NEXT_PUBLIC_GEOMAPID_API_KEY;

    useEffect(() => {
        const area = mapAreaRef.current;
        if (!area) return;
        const observer = new ResizeObserver(() => mapRef.current?.resize());
        observer.observe(area);
        return () => observer.disconnect();
    }, []);

    if (loading) {
        return (
            <div className="map-state"><span className="loading-spinner" />Memuat lokasi kamera...</div>
        );
    }

    if (error) {
        return (
            <div className="map-state error-state"><strong>Peta tidak dapat dimuat</strong><span>{error.message}</span></div>
        );
    }
    
    const segmentGeoJSON = { type: "FeatureCollection" as const, features: segments.map((segment) => {
        const update = segmentMap.get(segment.properties.segment_id);
        const pollutantTotals = update?.pollutant_totals ?? segment.properties.pollutant_totals;
        const calculatedTotal = pollutantTotals ? Object.values(pollutantTotals).reduce((sum, value) => sum + Number(value), 0) : null;
        return { ...segment, properties: { ...segment.properties, ...update, total_emission_g_h: update?.total_emission_g_h ?? segment.properties.total_emission_g_h ?? calculatedTotal } };
    }) };
    return (
        <div className={`map-panel-layout ${selectedCamera || selectedSegmentId ? "has-panel" : ""}`}>
        <div className="map-area" ref={mapAreaRef}>
            <Map ref={mapRef} mapLib={maplibregl} mapStyle={`https://basemap.mapid.io/styles/${style}/style.json?key=${geoMapidApiKey}`}
            initialViewState={{ longitude: 110.3695, latitude: -7.7956, zoom: 14 }} style={{ height: "100%", width: "100%" }} interactiveLayerIds={layerMode !== "cameras" ? ["segments-line"] : []}
            onMouseMove={(event) => { const feature = event.features?.find((item) => item.layer?.id === "segments-line"); setHoveredSegmentId(feature?.properties?.segment_id ?? null); }}
            onClick={(event) => { const feature = event.features?.find((item) => item.layer?.id === "segments-line"); if (feature?.properties?.segment_id) { setSelectedSegmentId(feature.properties.segment_id); setSelectedCamera(null); } }}>
            <NavigationControl position="bottom-right" showCompass={false} />
             {layerMode !== "cameras" && <Source id="segments" type="geojson" data={segmentGeoJSON}>
                 <Layer id="segments-line" type="line" paint={{ "line-color": ["case", ["==", ["get", "total_emission_g_h"], null], "#64748b", ["step", ["get", "total_emission_g_h"], "#22c55e", 1000, "#facc15", 5000, "#f97316", 20000, "#ef4444"]], "line-width": ["case", ["==", ["get", "segment_id"], hoveredSegmentId], 6, 3], "line-opacity": ["case", ["==", ["get", "segment_id"], hoveredSegmentId], 0.95, 0.72] }} />
             </Source>}
             {layerMode !== "segments" && cameras.map((camera) => {
                const emissionUpdate = emissionMap.get(
                    camera.properties.camera_id
                );
                 const emissionValue = emissionUpdate?.total_co2_g_per_min ?? 0;
                return (
                    <CameraMarker
                        key={camera.properties.id}
                        camera={camera}
                        color={getMarkerColor(emissionValue)}
                        onClick={() => { setSelectedCamera(camera); setSelectedSegmentId(null); }}
                        selected={selectedCamera?.properties.id === camera.properties.id}
                    />
                );
            })}
             <div className="map-layer-filters" role="group" aria-label="Filter lapisan peta">
                 {([["all", "Semua"], ["cameras", "CCTV kamera"], ["segments", "Segmen jalan"]] as const).map(([value, label]) => <label key={value} className={layerMode === value ? "active" : ""}><input type="radio" name="map-layer" checked={layerMode === value} onChange={() => setLayerMode(value)} /><span className="checkbox-indicator" />{label}</label>)}
             </div>
             <div className="segment-emission-legend" aria-label="Legenda emisi segmen"><strong>Emisi segmen</strong><span><i style={{ background: "#64748b" }} />Tidak tersedia</span><span><i style={{ background: "#22c55e" }} />&lt; 1.000 g/hr</span><span><i style={{ background: "#facc15" }} />1.000-4.999</span><span><i style={{ background: "#f97316" }} />5.000-19.999</span><span><i style={{ background: "#ef4444" }} />≥ 20.000</span></div>
             <button
                onClick={() => setStyle(s => s === "street-2d-building" ? "dark" : "street-2d-building")}
                className="map-style-toggle"
            >
                {isDark ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="5"/>
                        <line x1="12" y1="1" x2="12" y2="3"/>
                        <line x1="12" y1="21" x2="12" y2="23"/>
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                        <line x1="1" y1="12" x2="3" y2="12"/>
                        <line x1="21" y1="12" x2="23" y2="12"/>
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                    </svg>
                ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                    </svg>
                )}
                {isDark ? "Peta terang" : "Peta gelap"}
            </button>
         </Map>
        </div>
        {selectedCamera ? <SidePanel camera={selectedCamera} onClose={() => setSelectedCamera(null)} /> : <SegmentPanel segmentId={selectedSegmentId} onClose={() => setSelectedSegmentId(null)} />}
        </div>
    );
}
