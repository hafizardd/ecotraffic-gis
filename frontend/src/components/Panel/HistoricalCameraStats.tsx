"use client";

import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { HistoricalCameraEmission } from "@/types";
import { fmtDateTimeId, fmtIntId, formatNumber, formatSourceMode } from "@/utils/format";
import { ANALYTICS_NOTE_CLASS, POLLUTANT_DOT_CLASS, POLLUTANT_TEXT_CLASS, STAT_CARD_CLASS, STAT_GRID_CLASS, STAT_LABEL_CLASS, STAT_VALUE_CLASS } from "@/styles/tailwind";

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
            <p className={ANALYTICS_NOTE_CLASS}>
                {formatSourceMode(historical.source_mode)} dari segmen {historical.segment_id}, {fmtDateTimeId(historical.observed_at)}.
                {historical.is_interpolated ? " Nilai perkiraan jam, bukan arus langsung." : " Bukan arus langsung."}
            </p>
            <div className={STAT_GRID_CLASS}>
                {EMISSION_DEFINITIONS.map(({ key, label }) => (
                    <div key={key} className={`${STAT_CARD_CLASS} ${POLLUTANT_TEXT_CLASS[key]}`}>
                        <div className={STAT_LABEL_CLASS}><span className={POLLUTANT_DOT_CLASS} />{label}</div>
                        <div className={STAT_VALUE_CLASS}>
                            {emissions_g_per_min[key] == null ? "N/A" : formatNumber(Number(emissions_g_per_min[key]))}<small>g/min</small>
                        </div>
                    </div>
                ))}
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
                {VEHICLES.map(({ key, label }) => (
                    <div className="flex min-w-0 items-center justify-between gap-3 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-raised)] p-2.5 text-[10px] [&>span]:text-[var(--muted)] [&>strong]:font-[var(--font-data)] [&>strong]:text-right [&>strong]:text-[12px] [&>strong]:text-[var(--text)] [&>strong]:tabular-nums" key={key}>
                        <span>{label}/jam</span>
                        <strong>{volume_per_hour?.[key] == null ? "-" : fmtIntId(volume_per_hour[key])}</strong>
                    </div>
                ))}
            </div>
        </>
    );
}
