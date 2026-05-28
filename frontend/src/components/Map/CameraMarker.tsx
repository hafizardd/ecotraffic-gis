"use client"

import { useState } from "react"
import { Marker, Popup } from "react-map-gl/maplibre";
import { CameraFeature } from "@/types";

interface CameraMarkerProps {
    camera: CameraFeature;
    color: string;
    onClick: (camera: CameraFeature) => void;
    isDark?: boolean;
}

export default function CameraMarker({
    camera,
    color,
    onClick,
    isDark = false,
}: CameraMarkerProps) {
    const [showPopup, setShowPopup] = useState(false);
    const [longitude, latitude] = camera.geometry.coordinates;

    return(
        <>
            <Marker
                longitude={longitude}
                latitude={latitude}
                onClick={() => onClick(camera)}
            >
                <div
                    onMouseEnter={(e) => {
                        setShowPopup(true);
                        e.currentTarget.style.transform = "scale(1.35)";
                    }}
                    onMouseLeave={(e) => {
                        setShowPopup(false);
                        e.currentTarget.style.transform = "scale(1)";
                    }}
                    style={{
                        width: 16,
                        height: 16,
                        borderRadius: "100%",
                        backgroundColor: color,
                        border: "2px solid white",
                        boxShadow: "0 0 6px rgba(0,0,0,0.5)",
                        cursor: "pointer",
                        transition: "transform 0.15s",
                    }}
                />
            </Marker>
            {showPopup && (
                <Popup
                    longitude={longitude}
                    latitude={latitude}
                    closeButton={false}
                    closeOnClick={false}
                    offset={{ bottom: [0, -10] } as any}
                    className={isDark ? "popup-dark" : "popup-light"}
                >
                    {camera.properties.name}
                </Popup>
            )}
        </>
    );
}