"use client"

import { useState } from "react";

import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import CameraMarker from "./CameraMarker";
import SidePanel from "./SidePanel";
import { getMarkerColor } from "@/utils/markerColor";
import useCameras from "@/hooks/useCameras";
import { CameraFeature } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";

export default function MapView() {
    const {cameras, loading, error} = useCameras();
    const emissionMap = useEmissionsContext()
    const [selectedCamera, setSelectedCamera] = useState<CameraFeature | null>(null)

    const liveEmission = selectedCamera
        ? emissionMap.get(selectedCamera.properties.camera_id) ?? null
        : null;

    if(loading) {
        return <div className="flex items-center justify-center h-screen">Loading cameras...</div>
    }

    if (error) {
        return <div className="flex items-center justify-center h-screen text-red-500">Error: {error.message}</div>;
    }

    return (
        <MapContainer
        center={[-7.7956, 110.3695]}
        zoom={14}
        style={{ height: "100vh", width: "100%" }}
        >
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            {cameras.map((camera) => {
                const emissionUpdate = emissionMap.get(camera.properties.camera_id);
                const emissionValue = emissionUpdate?.total_co_g_per_min ?? 0;
                return (
                    <CameraMarker
                        key={camera.properties.id}
                        camera={camera}
                        color={getMarkerColor(emissionValue)}
                        onClick={() => setSelectedCamera(camera)}
                    />
                );
            })}
            <SidePanel
                camera={selectedCamera}
                onClose={() => setSelectedCamera(null)}
            />
        </MapContainer>
    );
}