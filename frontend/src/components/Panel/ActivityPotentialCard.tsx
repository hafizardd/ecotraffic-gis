"use client";

import { ActivityGridProperties } from "@/types";
import SectionTitle from "@/components/ui/SectionTitle";
import { classificationColor, classificationTier } from "@/constants/mapColors";
import { MISSING_LABEL, fmtFloatId, fmtIntId } from "@/utils/format";

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
            <div className="segment-overview">
                <strong>{label}</strong>
                <span>Peringkat {fmtIntId(properties.ranking)} dari {fmtIntId(properties.ranking_total ?? TOTAL_HEXES)}</span>
                <b className="priority-badge" style={{ background: badgeColor, color: badgeText }}>{label}</b>
            </div>
            {properties.data_status === "no_data" && (
                <p className="analytics-note">Tidak ada data kendaraan untuk jam ini; skor tidak dihitung.</p>
            )}
            {properties.data_status === "fallback" && (
                <p className="analytics-note">Perkiraan dari sel terdekat; tidak ada data kendaraan langsung untuk jam ini.</p>
            )}
            <section className="panel-section segment-decision-section">
                <SectionTitle title="Skor potensi AHP" meta={`Versi ${properties.ahp_weight_version}`} />
                <div className="segment-score"><span>SKOR TOTAL AHP</span><strong>{fmtFloatId(properties.skor_total_ahp, 2)}</strong></div>
            </section>
            <section className="panel-section">
                <SectionTitle title="Input ternormalisasi" meta="Skala 1–100 (dari model Excel)" />
                {Object.entries(INPUT_LABELS).map(([key, inputLabel]) => {
                    const raw = properties[key as keyof typeof properties];
                    const value = raw == null ? null : Number(raw);
                    const width = value == null ? 0 : Math.max(0, Math.min(100, value));
                    return (
                        <div className="criterion-card" key={key}>
                            <div className="criterion-card-header"><span>{inputLabel}</span><strong>{value == null ? MISSING_LABEL : fmtFloatId(value, 2)}</strong></div>
                            <div aria-hidden="true" style={{ height: 6, borderRadius: 3, background: "#e2e8f0", marginTop: 6 }}>
                                <div style={{ width: `${width}%`, height: "100%", borderRadius: 3, background: badgeColor }} />
                            </div>
                        </div>
                    );
                })}
            </section>
        </>
    );
}
