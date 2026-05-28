"use client";
import { useState } from "react";
import Map, { MapRef } from "react-map-gl/maplibre";
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

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                Loading cameras...
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-screen text-red-500">
                Error: {error.message}
            </div>
        );
    }
    
    return (
        <Map
            mapLib={maplibregl}
            mapStyle={`https://tiles.openfreemap.org/styles/${style}`}
            initialViewState={{
                longitude: 110.3695,
                latitude: -7.7956,
                zoom: 14,
            }}
            style={{ height: "100vh", width: "100%" }}
        >
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
                        isDark={isDark}
                    />
                );
            })}
            <button
                onClick={() => setStyle(s => s === "liberty" ? "dark" : "liberty")}
                className={`absolute top-4 right-4 z-10 flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium shadow-lg backdrop-blur-sm transition-colors hover:cursor-pointer ${
                    isDark
                        ? "bg-zinc-800/80 text-zinc-100 hover:bg-zinc-700/90"
                        : "bg-white/80 text-zinc-800 hover:bg-white/95"
                }`}
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
                {isDark ? "Bright" : "Dark"}
            </button>
            <SidePanel
                camera={selectedCamera}
                onClose={() => setSelectedCamera(null)}
            />
        </Map>
    );
}