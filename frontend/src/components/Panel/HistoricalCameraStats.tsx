"use client";

import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { HistoricalCameraEmission } from "@/types";
import { fmtDateTimeId, fmtIntId, formatNumber } from "@/utils/format";
import { ANALYTICS_NOTE_CLASS, POLLUTANT_DOT_CLASS, POLLUTANT_TEXT_CLASS, STAT_CARD_CLASS, STAT_GRID_CLASS, STAT_LABEL_CLASS, STAT_VALUE_CLASS } from "@/styles/tailwind";

const VEHICLES = [
    { key: "car", label: "Mobil" }, { key: "motorcycle", label: "Motor" },
    { key: "bus", label: "Bus" }, { key: "truck", label: "Truk" },
] as const;

// Historical (REPLAY) CCTV values borrowed from the camera's mapped segment.
// Explicitly labeled so a static number is never read as live traffic.
export default function HistoricalCameraStats({ historical }: { historical: HistoricalCameraEmission }) {
    const { emissions_g_per_min, volume_per_hour } = historical;
    return (
        <>
            <p className={ANALYTICS_NOTE_CLASS}>
                Nilai historis dari segmen {historical.segment_id} pada {fmtDateTimeId(historical.observed_at)}.
                {historical.is_interpolated ? " Hasil interpolasi jam, bukan arus live." : " Bukan arus live."}
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
            <div className="mt-3 grid grid-cols-2 gap-[9px]">
                {VEHICLES.map(({ key, label }) => (
                    <div className="flex min-w-0 items-center justify-between gap-3 rounded-[7px] border border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.68)] p-[10px] text-[10px] [&>span]:text-[#718198] [&>strong]:text-right [&>strong]:text-[11px] [&>strong]:text-[#dbe7f4] [&>strong]:tabular-nums" key={key}>
                        <span>{label}/jam</span>
                        <strong>{volume_per_hour?.[key] == null ? "-" : fmtIntId(volume_per_hour[key])}</strong>
                    </div>
                ))}
            </div>
        </>
    );
}
