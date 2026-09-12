"use client";

import { ActivityGridProperties } from "@/types";
import SectionTitle from "@/components/ui/SectionTitle";
import { classificationColor, classificationTier } from "@/constants/mapColors";
import { MISSING_LABEL, fmtFloatId, fmtIntId } from "@/utils/format";
import { ANALYTICS_NOTE_CLASS, PANEL_SECTION_CLASS } from "@/styles/tailwind";

export const TOTAL_HEXES = 378;
export const INPUT_LABELS: Record<string, string> = {
    norm_volume: "Volume kendaraan",
    norm_poi: "Jumlah POI",
    norm_penduduk: "Jumlah penduduk",
};

// Shared visual language for the hex activity-potential model, used by both the
// grid panel and the segment panel so the two views cannot drift.
export default function ActivityPotentialCard({ properties }: { properties: ActivityGridProperties }) {
    const tier = classificationTier(properties.klasifikasi_potensi);
    const badgeColor = classificationColor(properties.klasifikasi_potensi);
    const badgeText = tier >= 4 ? "#ffffff" : "#0f172a";
    const label = properties.klasifikasi_potensi ?? MISSING_LABEL;
    return (
        <>
            <div className="mx-4 mt-[10px] grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-[10px] gap-y-1.5 rounded-[9px] border border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.88)] px-[13px] py-3 max-[420px]:mx-[14px]">
                <strong className="min-w-0 text-sm leading-[1.35] [overflow-wrap:anywhere]">{label}</strong>
                <span className="whitespace-nowrap text-right text-[11px] leading-[1.35] text-[var(--secondary)]">Peringkat {fmtIntId(properties.ranking)} dari {fmtIntId(properties.ranking_total ?? TOTAL_HEXES)}</span>
                <b className="col-span-full mt-[3px] inline-flex w-max items-center rounded-[5px] px-[7px] py-1 text-[8px] font-extrabold tracking-[0.06em] uppercase" style={{ background: badgeColor, color: badgeText }}>{label}</b>
            </div>
            {properties.data_status === "no_data" && (
                <p className={ANALYTICS_NOTE_CLASS}>Tidak ada data kendaraan untuk jam ini; skor tidak dihitung.</p>
            )}
            {properties.data_status === "fallback" && (
                <p className={ANALYTICS_NOTE_CLASS}>Perkiraan dari sel terdekat; tidak ada data kendaraan langsung untuk jam ini.</p>
            )}
            <section className={`${PANEL_SECTION_CLASS} px-4 py-5 last:border-b-0 max-[420px]:px-[14px] max-[420px]:py-[18px]`}>
                <SectionTitle title="Skor potensi AHP" />
                <div className="flex min-h-[52px] items-center justify-between gap-4 rounded-[9px] border border-[rgba(34,197,94,0.18)] bg-[rgba(34,197,94,0.055)] px-[13px] py-[11px]"><span className="text-[10px] font-extrabold leading-[1.2] tracking-[0.08em] text-[#7f8fa5]">SKOR TOTAL AHP</span><strong className="text-right text-xl leading-none text-[#4ade80] tabular-nums">{fmtFloatId(properties.skor_total_ahp, 2)}</strong></div>
            </section>
            <section className={`${PANEL_SECTION_CLASS} px-4 py-5 last:border-b-0 max-[420px]:px-[14px] max-[420px]:py-[18px]`}>
                <SectionTitle title="Input ternormalisasi" meta="Skala 1–100 (dari model Excel)" />
                {Object.entries(INPUT_LABELS).map(([key, inputLabel]) => {
                    const raw = properties[key as keyof typeof properties];
                    const value = raw == null ? null : Number(raw);
                    const width = value == null ? 0 : Math.max(0, Math.min(100, value));
                    return (
                        <div className="mb-2 flex flex-col gap-2 rounded-lg border border-[rgba(148,163,184,0.1)] bg-[rgba(14,29,46,0.75)] px-[13px] py-3 tabular-nums [overflow-wrap:anywhere]" key={key}>
                            <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-baseline gap-3 [&>span]:text-[11px] [&>span]:font-bold [&>span]:leading-[1.35] [&>span]:text-[#dbeafe] [&>strong]:text-right [&>strong]:text-[17px] [&>strong]:leading-[1.1] [&>strong]:text-[var(--text)]"><span>{inputLabel}</span><strong>{value == null ? MISSING_LABEL : fmtFloatId(value, 2)}</strong></div>
                            <div aria-hidden="true" className="mt-1.5 h-1.5 rounded-[3px] bg-[#e2e8f0]">
                                <div className="h-full rounded-[3px]" style={{ width: `${width}%`, background: badgeColor }} />
                            </div>
                        </div>
                    );
                })}
            </section>
        </>
    );
}
