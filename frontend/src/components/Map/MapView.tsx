"use client"

import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import CameraMarker from "./CameraMarker";
import { getMarkerColor } from "@/utils/markerColor";
import useCameras from "@/hooks/useCameras";

export default function MapView() {
    const {cameras, loading, error} = useCameras();

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
            {cameras.map((camera) => (
                <CameraMarker
                key={camera.properties.id}
                camera={camera}
                color={getMarkerColor(0)}
                onClick={() => {}}
                />
            ))}
        </MapContainer>
    );
}