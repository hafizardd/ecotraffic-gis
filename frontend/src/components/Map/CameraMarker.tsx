"use client"

import { useState } from "react"
import { Marker, Popup } from "react-map-gl/maplibre";
import { CameraFeature } from "@/types";

interface CameraMarkerProps {
    camera: CameraFeature;
    color: string;
    onClick: (camera: CameraFeature) => void;
    selected?: boolean;
}

export default function CameraMarker({
    camera,
    color,
    onClick,
    selected = false,
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
                <button
                    type="button"
                    aria-label={`Buka detail ${camera.properties.name}`}
                    className={`camera-marker ${selected ? "selected" : ""}`}
                    onMouseEnter={() => {
                        setShowPopup(true);
                    }}
                    onMouseLeave={() => {
                        setShowPopup(false);
                    }}
                    style={{ "--marker-color": color } as React.CSSProperties}
                ><span /></button>
            </Marker>
            {(showPopup || selected) && (
                <Popup
                    longitude={longitude}
                    latitude={latitude}
                    closeButton={false}
                    closeOnClick={false}
                    offset={12}
                    className="popup-dark"
                >
                    <div className="marker-popup"><strong>{camera.properties.name}</strong>{camera.properties.is_active && <span><i /> Live</span>}<small>Klik untuk melihat detail</small></div>
                </Popup>
            )}
        </>
    );
}
