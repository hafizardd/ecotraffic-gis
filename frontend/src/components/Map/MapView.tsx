"use client";
import { useEffect, useRef, useState } from "react";
import Map, { MapRef, NavigationControl } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import CameraMarker from "./CameraMarker";
import SidePanel from "../Panel/SidePanel";
import { getMarkerColor } from "@/utils/markerColor";
import useCameras from "@/hooks/useCameras";
import { CameraFeature } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";

export default function MapView() {
    const { cameras, loading, error } = useCameras();
    const emissionMap = useEmissionsContext();
    const [selectedCamera, setSelectedCamera] = useState<CameraFeature | null>(null);
    const [style, setStyle] = useState<"liberty" | "dark">("liberty");
    const isDark = style === "dark";
    const mapRef = useRef<MapRef>(null);
    const mapAreaRef = useRef<HTMLDivElement>(null);

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
    
    return (
        <div className={`map-panel-layout ${selectedCamera ? "has-panel" : ""}`}>
        <div className="map-area" ref={mapAreaRef}>
        <Map ref={mapRef} mapLib={maplibregl} mapStyle={`https://tiles.openfreemap.org/styles/${style}`}
            initialViewState={{ longitude: 110.3695, latitude: -7.7956, zoom: 14 }} style={{ height: "100%", width: "100%" }}>
            <NavigationControl position="bottom-right" showCompass={false} />
            {cameras.map((camera) => {
                const emissionUpdate = emissionMap.get(
                    camera.properties.camera_id
                );
                const emissionValue =
                    emissionUpdate?.total_co_g_per_min ?? 0;
                return (
                    <CameraMarker
                        key={camera.properties.id}
                        camera={camera}
                        color={getMarkerColor(emissionValue)}
                        onClick={() => setSelectedCamera(camera)}
                        selected={selectedCamera?.properties.id === camera.properties.id}
                    />
                );
            })}
            <button
                onClick={() => setStyle(s => s === "liberty" ? "dark" : "liberty")}
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
        <SidePanel camera={selectedCamera} onClose={() => setSelectedCamera(null)} />
        </div>
    );
}
