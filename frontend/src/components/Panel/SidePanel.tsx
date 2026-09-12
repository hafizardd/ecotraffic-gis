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
import { ANALYTICS_NOTE_CLASS, ESTIMATE_BADGE_CLASS, PANEL_CLASS, PANEL_CLOSE_CLASS, PANEL_CONTENT_CLASS, PANEL_HEADER_CLASS, PANEL_ICON_CLASS, PANEL_SECTION_CLASS, PANEL_TITLE_CLASS, SEGMENT_STATE_CLASS } from "@/styles/tailwind";

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
        <aside className={PANEL_CLASS} aria-label={`Detail CCTV ${camera.properties.name}`}>
            <div className={PANEL_HEADER_CLASS}>
                <div className={PANEL_ICON_CLASS}><MapPin aria-hidden="true" /></div>
                <div className={PANEL_TITLE_CLASS}><span>CCTV terpilih</span><h2>{camera.properties.name}</h2></div>
                {isTrackingSource && <div className={`hidden items-center gap-1.5 pr-1 text-[9px] font-bold tracking-[0.08em] uppercase min-[980px]:flex ${trackingStatus === "error" ? "text-[#fca5a5]" : "text-(--brand-strong)"}`} role="status">
                    <i className={`h-1.5 w-1.5 rounded-full ${trackingStatus === "error" ? "bg-(--danger)" : "bg-(--green)"}`} /> {trackingStatus === "error" ? "Terputus" : "Visual live"}
                </div>}
                <button
                    onClick={onClose}
                    className={PANEL_CLOSE_CLASS}
                    aria-label="Tutup panel monitoring"
                >
                    <X aria-hidden="true" />
                </button>
            </div>

            <div className={PANEL_CONTENT_CLASS}>
                {isTrackingSource && <section className={PANEL_SECTION_CLASS}>
                    <SectionTitle title="Pelacakan visual" meta="Deteksi dan tracking kendaraan real-time" />
                    <VideoFeed key={camera.properties.camera_id} cameraId={camera.properties.camera_id} onStatusChange={setTrackingStatus} />
                </section>}
                {liveEmission ? (
                    <>
                        <section className={PANEL_SECTION_CLASS}>
                            <SectionTitle title="Emisi saat ini" meta="Nilai dalam g/min" />
                            <EmissionStats cameraId={camera.properties.camera_id} />
                        </section>
                        <section className={PANEL_SECTION_CLASS}>
                            <SectionTitle title="Deteksi kendaraan" meta="Hitungan kendaraan terkini" />
                            <VehicleCount emission={liveEmission} />
                        </section>
                        <section className={`${PANEL_SECTION_CLASS} border-b-0`}>
                            <SectionTitle title="Tren emisi" meta="Monitoring emisi real-time" />
                            <EmissionChart cameraId={camera.properties.camera_id} liveEmission={liveEmission} />
                        </section>
                    </>
                ) : historical ? (
                    <section className={PANEL_SECTION_CLASS}>
                        <SectionTitle title="Emisi statis" meta="Nilai dalam g/min (data tidak langsung)" />
                        <HistoricalCameraStats historical={historical} />
                    </section>
                ) : estimate ? (
                    <section className={`${PANEL_SECTION_CLASS} bg-[rgba(245,165,36,0.025)]`}>
                        <SectionTitle
                            title="Perkiraan dari data sekitar"
                            meta={`Kamera ${estimate.cameraName}, sekitar ${formatNumber(estimate.distanceKm)} km`}
                            aside={<b className={ESTIMATE_BADGE_CLASS}>Perkiraan</b>}
                        />
                        <p className={ANALYTICS_NOTE_CLASS}>
                            Kamera ini belum punya pembacaan sendiri. Nilai berikut diperkirakan dari kamera terdekat, bukan arus langsung kamera ini.
                        </p>
                        {estimate.emission ? (
                            <>
                                <EmissionStats cameraId={camera.properties.camera_id} emission={estimate.emission} />
                                <div className="h-3" />
                                <VehicleCount emission={estimate.emission} />
                            </>
                        ) : estimate.historical ? (
                            <HistoricalCameraStats historical={estimate.historical} />
                        ) : null}
                    </section>
                ) : (
                    <div className={SEGMENT_STATE_CLASS} role="status">
                        <strong>Belum ada data</strong>
                        <span>Kamera ini belum mengirim pembacaan dan tidak ada kamera sekitar dengan data untuk diperkirakan.</span>
                    </div>
                )}
            </div>
        </aside>
    );
}
