"use client";

import { useState } from "react";
import { MapPin, X } from "lucide-react";
import { CameraFeature, HistoricalCameraEmission } from "@/types";
import VideoFeed from "./VideoFeed";
import EmissionStats from "./EmissionStats";
import VehicleCount from "./VehicleCount";
import HistoricalCameraStats from "./HistoricalCameraStats";
import { useEmissionsContext } from "@/context/EmissionsContext";
import EmissionChart from "./EmissionChart";
import SectionTitle from "@/components/ui/SectionTitle";
import type { NeighborEstimate } from "@/utils/cameraEstimate";
import { formatNumber } from "@/utils/format";

interface SidePanelProps {
    camera: CameraFeature | null;
    historical?: HistoricalCameraEmission | null;
    estimate?: NeighborEstimate | null;
    onClose: () => void;
}

export default function SidePanel({ camera, historical = null, estimate = null, onClose }: SidePanelProps) {
    const { emissionMap } = useEmissionsContext();
    const [trackingStatus, setTrackingStatus] = useState<"loading" | "streaming" | "error">("loading");
    const liveEmission = camera
        ? emissionMap.get(camera.properties.camera_id) ?? null
        : null;

    if (!camera) return null;

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
                <section className="panel-section video-section">
                    {isTrackingSource && <><SectionTitle title="Pelacakan visual" meta="Deteksi dan tracking kendaraan real-time" /><VideoFeed key={camera.properties.camera_id} cameraId={camera.properties.camera_id} onStatusChange={setTrackingStatus} /></>}
                </section>
                {liveEmission ? (
                    <>
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
                    </>
                ) : historical ? (
                    <section className="panel-section">
                        <SectionTitle title="Emisi statis" meta="Nilai dalam g/min (data tidak langsung)" />
                        <HistoricalCameraStats historical={historical} />
                    </section>
                ) : estimate ? (
                    <section className="panel-section estimate-section">
                        <SectionTitle
                            title="Perkiraan dari data sekitar"
                            meta={`Kamera ${estimate.cameraName}, sekitar ${formatNumber(estimate.distanceKm)} km`}
                            aside={<b className="estimate-badge">Perkiraan</b>}
                        />
                        <p className="analytics-note">
                            Kamera ini belum punya pembacaan sendiri. Nilai berikut diperkirakan dari kamera terdekat, bukan arus langsung kamera ini.
                        </p>
                        {estimate.emission ? (
                            <>
                                <EmissionStats cameraId={camera.properties.camera_id} emission={estimate.emission} />
                                <div style={{ height: 12 }} />
                                <VehicleCount emission={estimate.emission} />
                            </>
                        ) : estimate.historical ? (
                            <HistoricalCameraStats historical={estimate.historical} />
                        ) : null}
                    </section>
                ) : (
                    <div className="segment-state" role="status">
                        <strong>Belum ada data</strong>
                        <span>Kamera ini belum mengirim pembacaan dan tidak ada kamera sekitar dengan data untuk diperkirakan.</span>
                    </div>
                )}
            </div>
        </aside>
    );
}
