"use client";

import { ActivityGridProperties } from "@/types";
import SectionTitle from "@/components/ui/SectionTitle";
import { activityGradientCss, classificationColor, classificationTier } from "@/constants/mapColors";
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
    const score = properties.skor_total_ahp == null ? null : Number(properties.skor_total_ahp);
    const scorePosition = score == null ? 0 : Math.max(0, Math.min(100, score));
    return (
        <>
            <div className={SEGMENT_OVERVIEW_CLASS}>
                <strong>{label}</strong>
                <span>Peringkat {fmtIntId(properties.ranking)} dari {fmtIntId(properties.ranking_total ?? TOTAL_HEXES)}</span>
                <b className="col-span-full inline-flex w-max items-center rounded-(--radius-badge) px-2 py-1 text-[9px] font-bold tracking-[0.06em] uppercase" style={{ background: badgeColor, color: badgeText }}>{label}</b>
            </div>
            {properties.data_status === "no_data" && (
                <p className={`${ANALYTICS_NOTE_CLASS} mx-4`}>Tidak ada data kendaraan untuk jam ini; skor tidak dihitung.</p>
            )}
            {properties.data_status === "fallback" && (
                <p className={`${ANALYTICS_NOTE_CLASS} mx-4`}>Perkiraan dari area terdekat; tidak ada data kendaraan langsung untuk jam ini.</p>
            )}
            <section className={SEGMENT_SECTION_CLASS}>
                <SectionTitle title="Skor potensi" meta="Indikator utama potensi aktivitas" />
                <div className="rounded-md border border-(--border) bg-(--surface-raised) px-3.5 py-3" role="meter" aria-label="Skor total potensi aktivitas" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score ?? undefined}>
                    <div className="flex min-h-9 items-end justify-between gap-4">
                        <span className="text-[10px] font-bold leading-4 tracking-[0.08em] text-(--muted) uppercase">SKOR TOTAL</span>
                        <strong className="font-(family-name:--font-data) text-[30px] leading-none font-semibold tracking-[-0.03em] text-(--text) tabular-nums">{fmtFloatId(properties.skor_total_ahp, 2)}</strong>
                    </div>
                    <div className="relative mt-4 h-2 rounded-(--radius-badge)" style={{ background: activityGradientCss() }} aria-hidden="true">
                        {score !== null && <span className="absolute top-1/2 h-4 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full border border-(--text) bg-(--canvas) shadow-[0_0_0_2px_rgba(9,26,34,0.6)]" style={{ left: `${scorePosition}%` }} />}
                    </div>
                    <div className="mt-1.5 flex justify-between font-(family-name:--font-data) text-[9px] text-(--muted) tabular-nums"><span>0 · rendah</span><span>100 · tinggi</span></div>
                </div>
            </section>
            <section className={SEGMENT_SECTION_CLASS}>
                <SectionTitle title="Input ternormalisasi" meta="Skala 1–100 (dari model Excel)" />
                {Object.entries(INPUT_LABELS).map(([key, inputLabel]) => {
                    const raw = properties[key as keyof typeof properties];
                    const value = raw == null ? null : Number(raw);
                    const width = value == null ? 0 : Math.max(0, Math.min(100, value));
                    return (
                        <div className="mb-2 flex flex-col gap-2 rounded-sm border border-(--border) bg-(--surface-raised) px-3 py-3 tabular-nums [overflow-wrap:anywhere] last:mb-0" key={key}>
                            <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-baseline gap-3 [&>span]:text-[11px] [&>span]:font-semibold [&>span]:leading-[1.35] [&>span]:text-(--secondary) [&>strong]:font-(family-name:--font-data) [&>strong]:text-right [&>strong]:text-[17px] [&>strong]:leading-[1.1] [&>strong]:text-(--text)"><span>{inputLabel}</span><strong>{value == null ? MISSING_LABEL : fmtFloatId(value, 2)}</strong></div>
                            <div role="progressbar" aria-label={`${inputLabel}: ${value == null ? MISSING_LABEL : fmtFloatId(value, 2)}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value ?? undefined} className="mt-1 h-1.5 overflow-hidden rounded-(--radius-badge) bg-(--canvas)">
                                <div className="h-full rounded-(--radius-badge)" style={{ width: `${width}%`, background: badgeColor }} />
                            </div>
                        </div>
                    );
                })}
            </section>
        </>
    );
}
