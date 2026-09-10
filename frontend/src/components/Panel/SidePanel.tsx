"use client";

import { useState } from "react";
import { MapPin, X } from "lucide-react";
import { CameraFeature } from "@/types";
import VideoFeed from "./VideoFeed";
import EmissionStats from "./EmissionStats";
import VehicleCount from "./VehicleCount";
import { useEmissionsContext } from "@/context/EmissionsContext";
import EmissionChart from "./EmissionChart";
import SectionTitle from "@/components/ui/SectionTitle";

interface SidePanelProps {
    camera: CameraFeature | null;
    onClose: () => void;
}

export default function SidePanel({ camera, onClose }: SidePanelProps) {
    const { emissionMap } = useEmissionsContext();
    const [trackingStatus, setTrackingStatus] = useState<"loading" | "streaming" | "error">("loading");
    const liveEmission = camera
        ? emissionMap.get(camera.properties.camera_id) ?? null
        : null;

    if (!camera) return null;

    const freshnessStatus = liveEmission?.freshness_status ?? camera.properties.freshness_status;
    const ageSeconds = liveEmission?.data_age_seconds ?? camera.properties.data_age_seconds;
    const isTrackingSource = camera.properties.data_source === "LIVE";

    return (
        <aside className="monitoring-panel">
            <div className="panel-header">
                <div className="panel-location-icon"><MapPin aria-hidden="true" /></div>
                <div className="panel-title"><span>LOKASI TERPILIH</span><h2>{camera.properties.name}</h2></div>
                {isTrackingSource && <div className={`panel-tracking ${trackingStatus === "error" ? "panel-tracking-error" : ""}`}>
                    <i /> {trackingStatus === "error" ? "TRACKING TERPUTUS" : "PELACAKAN VISUAL"}
                </div>}
                <button
                    onClick={onClose}
                    className="panel-close"
                    aria-label="Tutup panel monitoring"
                >
                    <X aria-hidden="true" />
                </button>
            </div>

            <div className="panel-content">
                <div className="panel-data-status" aria-live="polite">
                    <span>DATA {freshnessStatus.toUpperCase()}</span>
                    <small>{ageSeconds == null ? "Belum ada data" : `${ageSeconds}s sejak capture terakhir`}</small>
                </div>
                <section className="panel-section video-section">
                    {isTrackingSource && <><SectionTitle title="Pelacakan visual" meta="Deteksi dan tracking kendaraan real-time" /><VideoFeed key={camera.properties.camera_id} cameraId={camera.properties.camera_id} onStatusChange={setTrackingStatus} /></>}
                </section>
                <section className="panel-section">
                    <SectionTitle title="Emisi saat ini" meta="Nilai dalam g/min" />
                    <EmissionStats cameraId={camera.properties.camera_id} />
                </section>
                <section className="panel-section">
                    <SectionTitle title="Deteksi kendaraan" meta="Hitungan kendaraan terkini" />
                    <VehicleCount emission={liveEmission} />
                </section>
                <section className="panel-section chart-section">
                    <SectionTitle title="Tren emisi" meta="Monitoring emisi real-time" />
                    <EmissionChart cameraId={camera.properties.camera_id} liveEmission={liveEmission} />
                </section>
            </div>
        </aside>
    );
}
