"use client";

import { ActivityGridProperties } from "@/types";
import SectionTitle from "@/components/ui/SectionTitle";
import { classificationColor, classificationTier } from "@/constants/mapColors";
import { MISSING_LABEL, fmtFloatId, fmtIntId } from "@/utils/format";
import { ANALYTICS_NOTE_CLASS, SEGMENT_OVERVIEW_CLASS, SEGMENT_SECTION_CLASS } from "@/styles/tailwind";

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
            <div className={SEGMENT_OVERVIEW_CLASS}>
                <strong>{label}</strong>
                <span>Peringkat {fmtIntId(properties.ranking)} dari {fmtIntId(properties.ranking_total ?? TOTAL_HEXES)}</span>
                <b className="col-span-full inline-flex w-max items-center rounded-[var(--radius-badge)] px-2 py-1 text-[9px] font-bold tracking-[0.06em] uppercase" style={{ background: badgeColor, color: badgeText }}>{label}</b>
            </div>
            {properties.data_status === "no_data" && (
                <p className={`${ANALYTICS_NOTE_CLASS} mx-4`}>Tidak ada data kendaraan untuk jam ini; skor tidak dihitung.</p>
            )}
            {properties.data_status === "fallback" && (
                <p className={`${ANALYTICS_NOTE_CLASS} mx-4`}>Perkiraan dari sel terdekat; tidak ada data kendaraan langsung untuk jam ini.</p>
            )}
            <section className={SEGMENT_SECTION_CLASS}>
                <SectionTitle title="Skor potensi AHP" meta="Indikator utama potensi aktivitas" />
                <div className="flex min-h-[66px] items-end justify-between gap-4 rounded-[var(--radius-md)] border border-[rgba(34,197,94,0.24)] bg-[var(--brand-soft)] px-3.5 py-3">
                    <span className="text-[10px] font-bold leading-4 tracking-[0.08em] text-[var(--muted)] uppercase">Skor total</span>
                    <strong className="font-[var(--font-data)] text-[28px] leading-none font-semibold tracking-[-0.03em] text-[var(--brand-strong)] tabular-nums">{fmtFloatId(properties.skor_total_ahp, 2)}</strong>
                </div>
            </section>
            <section className={SEGMENT_SECTION_CLASS}>
                <SectionTitle title="Input ternormalisasi" meta="Skala 1–100 (dari model Excel)" />
                {Object.entries(INPUT_LABELS).map(([key, inputLabel]) => {
                    const raw = properties[key as keyof typeof properties];
                    const value = raw == null ? null : Number(raw);
                    const width = value == null ? 0 : Math.max(0, Math.min(100, value));
                    return (
                        <div className="mb-2 flex flex-col gap-2 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-3 tabular-nums [overflow-wrap:anywhere] last:mb-0" key={key}>
                            <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-baseline gap-3 [&>span]:text-[11px] [&>span]:font-semibold [&>span]:leading-[1.35] [&>span]:text-[var(--secondary)] [&>strong]:font-[var(--font-data)] [&>strong]:text-right [&>strong]:text-[17px] [&>strong]:leading-[1.1] [&>strong]:text-[var(--text)]"><span>{inputLabel}</span><strong>{value == null ? MISSING_LABEL : fmtFloatId(value, 2)}</strong></div>
                            <div aria-hidden="true" className="mt-1 h-1.5 overflow-hidden rounded-[var(--radius-badge)] bg-[var(--canvas)]">
                                <div className="h-full rounded-[var(--radius-badge)]" style={{ width: `${width}%`, background: badgeColor }} />
                            </div>
                        </div>
                    );
                })}
            </section>
        </>
    );
}
