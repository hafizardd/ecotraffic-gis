"use client";

import { CameraFeature } from "@/types";
import VideoFeed from "./VideoFeed";
import EmissionStats from "./EmissionStats";
import VehicleCount from "./VehicleCount";
import { useEmissionsContext } from "@/context/EmissionsContext";
import EmissionChart from "./EmissionChart";

interface SidePanelProps {
    camera: CameraFeature | null;
    onClose: () => void;
}

export default function SidePanel({ camera, onClose }: SidePanelProps) {
    const { emissionMap } = useEmissionsContext();
    const liveEmission = camera
        ? emissionMap.get(camera.properties.camera_id) ?? null
        : null;

    if (!camera) return null;

    const healthStatus = camera.properties.status;
    const freshnessStatus = liveEmission?.freshness_status ?? camera.properties.freshness_status;
    const ageSeconds = liveEmission?.data_age_seconds ?? camera.properties.data_age_seconds;

    return (
        <aside className="monitoring-panel">
            <div className="panel-header">
                <div className="panel-location-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg></div>
                <div className="panel-title"><span>LOKASI TERPILIH</span><h2>{camera.properties.name}</h2></div>
                <div className={`panel-live panel-health-${healthStatus}`}>
                    <i /> {healthStatus.toUpperCase()}
                </div>
                <button
                    onClick={onClose}
                    className="panel-close"
                    aria-label="Tutup panel monitoring"
                >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <div className="panel-content">
                <div className="panel-data-status" aria-live="polite">
                    <span>DATA {freshnessStatus.toUpperCase()}</span>
                    <small>{ageSeconds == null ? "Belum ada data" : `${ageSeconds}s sejak capture terakhir`}</small>
                </div>
                <section className="panel-section video-section">
                    {camera.properties.data_source === "LIVE" && <><div className="section-heading"><div><span>LIVE CAMERA</span><small>Streaming pemantauan lokasi</small></div></div><VideoFeed streamUrl={camera.properties.stream_url} /></>}
                </section>
                <section className="panel-section">
                    <div className="section-heading"><div><span>CURRENT EMISSIONS</span><small>Emisi saat ini dalam g/min</small></div></div>
                    <EmissionStats cameraId={camera.properties.camera_id} />
                </section>
                <section className="panel-section">
                    <div className="section-heading"><div><span>VEHICLE COUNT</span><small>Deteksi kendaraan terkini</small></div></div>
                    <VehicleCount emission={liveEmission} />
                </section>
                <section className="panel-section chart-section">
                    <div className="section-heading"><div><span>EMISSION TREND</span><small>Monitoring emisi real-time</small></div></div>
                    <EmissionChart cameraId={camera.properties.camera_id} liveEmission={liveEmission} />
                </section>
            </div>
        </aside>
    );
}
