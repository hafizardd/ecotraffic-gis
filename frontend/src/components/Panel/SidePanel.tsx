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
import { ANALYTICS_NOTE_CLASS, DATA_EMPTY_CLASS, ESTIMATE_BADGE_CLASS, PANEL_CLASS, PANEL_CLOSE_CLASS, PANEL_CONTENT_CLASS, PANEL_HEADER_CLASS, PANEL_ICON_CLASS, PANEL_SECTION_CLASS, PANEL_TITLE_CLASS } from "@/styles/tailwind";

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
        <aside className={PANEL_CLASS}>
            <div className={PANEL_HEADER_CLASS}>
                <div className={PANEL_ICON_CLASS}><MapPin aria-hidden="true" /></div>
                <div className={PANEL_TITLE_CLASS}><span>LOKASI TERPILIH</span><h2>{camera.properties.name}</h2></div>
                {isTrackingSource && <div className={`flex items-center gap-2 pr-1 text-[9px] font-extrabold tracking-[0.12em] ${trackingStatus === "error" ? "text-[#f05252]" : "text-[#4ade80]"}`}>
                    <i className={`h-[7px] w-[7px] rounded-full ${trackingStatus === "error" ? "bg-[#f05252] shadow-[0_0_0_4px_rgba(240,82,82,0.12)]" : "bg-[var(--green)] shadow-[0_0_0_4px_rgba(34,197,94,0.12)]"}`} /> {trackingStatus === "error" ? "TRACKING TERPUTUS" : "PELACAKAN VISUAL"}
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
                <section className={PANEL_SECTION_CLASS}>
                    {isTrackingSource && <><SectionTitle title="Pelacakan visual" meta="Deteksi dan tracking kendaraan real-time" /><VideoFeed key={camera.properties.camera_id} cameraId={camera.properties.camera_id} onStatusChange={setTrackingStatus} /></>}
                </section>
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
                        <SectionTitle title="Emisi historis" meta="Nilai dalam g/min (profil replay)" />
                        <HistoricalCameraStats historical={historical} />
                    </section>
                ) : estimate ? (
                    <section className={`${PANEL_SECTION_CLASS} bg-[rgba(245,165,36,0.025)]`}>
                        <SectionTitle
                            title="Estimasi dari data sekitar"
                            meta={`Kamera ${estimate.cameraName}, sekitar ${formatNumber(estimate.distanceKm)} km`}
                            aside={<b className={ESTIMATE_BADGE_CLASS}>Estimasi</b>}
                        />
                        <p className={ANALYTICS_NOTE_CLASS}>
                            Kamera ini belum punya pembacaan sendiri. Nilai berikut diperkirakan dari kamera terdekat, bukan arus live kamera ini.
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
                    <div className={`${DATA_EMPTY_CLASS} m-5 flex-col px-4 text-center [&>strong]:text-[#cbd5e1] [&>strong]:text-xs [&>span]:text-[10px]`} role="status">
                        <strong>Belum ada data</strong>
                        <span>Kamera ini belum mengirim pembacaan dan tidak ada kamera sekitar dengan data untuk diperkirakan.</span>
                    </div>
                )}
            </div>
        </aside>
    );
}
