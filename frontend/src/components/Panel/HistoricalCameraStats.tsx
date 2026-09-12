"use client";

import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { HistoricalCameraEmission } from "@/types";
import { fmtDateTimeId, fmtIntId, formatNumber, formatSourceMode } from "@/utils/format";

const VEHICLES = [
    { key: "car", label: "Mobil" }, { key: "motorcycle", label: "Motor" },
    { key: "bus", label: "Bus" }, { key: "truck", label: "Truk" },
] as const;

// Static CCTV values borrowed from the camera's mapped segment. Explicitly
// labeled so a static number is never read as live traffic.
export default function HistoricalCameraStats({ historical }: { historical: HistoricalCameraEmission }) {
    const { emissions_g_per_min, volume_per_hour } = historical;
    return (
        <>
            <p className="analytics-note">
                {formatSourceMode(historical.source_mode)} dari segmen {historical.segment_id}, {fmtDateTimeId(historical.observed_at)}.
                {historical.is_interpolated ? " Nilai perkiraan jam, bukan arus langsung." : " Bukan arus langsung."}
            </p>
            <div className="stat-grid">
                {EMISSION_DEFINITIONS.map(({ key, label }) => (
                    <div key={key} className={`stat-card pollutant-${key}`}>
                        <div className="stat-label"><span className="pollutant-dot" />{label}</div>
                        <div className="stat-value">
                            {emissions_g_per_min[key] == null ? "N/A" : formatNumber(Number(emissions_g_per_min[key]))}<small>g/min</small>
                        </div>
                    </div>
                ))}
            </div>
            <div className="criteria-grid">
                {VEHICLES.map(({ key, label }) => (
                    <div className="criteria-item" key={key}>
                        <span>{label}/jam</span>
                        <strong>{volume_per_hour?.[key] == null ? "-" : fmtIntId(volume_per_hour[key])}</strong>
                    </div>
                ))}
            </div>
        </>
    );
}
