"use client";

import { useEffect, useState } from "react";
import { Bus, X } from "lucide-react";
import { fetchBusStopDetail } from "@/services/api";
import { BusStopDetail } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import { interventionColor, readableTextOn } from "@/constants/mapColors";
import { MISSING_LABEL, fmtDateTimeId, fmtFloatId, fmtIntId } from "@/utils/format";
import AutoInsightCard from "@/components/Panel/AutoInsightCard";
import { CRITERIA_GRID_CLASS, DATA_MISSING_CLASS, PANEL_CLASS, PANEL_CLOSE_CLASS, PANEL_ICON_CLASS, SEGMENT_EMPTY_CLASS, SEGMENT_OVERVIEW_CLASS, SEGMENT_PANEL_CONTENT_CLASS, SEGMENT_PANEL_HEADER_CLASS, SEGMENT_PANEL_TITLE_CLASS, SEGMENT_SECTION_CLASS, SEGMENT_STATE_CLASS, STAT_CARD_CLASS, STAT_GRID_CLASS } from "@/styles/tailwind";

const COMPONENTS: { keys: (keyof BusStopDetail)[]; label: string }[] = [
    { keys: ["accessibility_score_100", "accessibility_score"], label: "Aksesibilitas (survei 0-100)" },
    { keys: ["condition_score_100", "facility_score"], label: "Kondisi / fasilitas" },
    { keys: ["environment_score_100", "environment_score"], label: "Lingkungan" },
];

const FACILITY_LABELS: Record<string, string> = {
    atap_shelter: "Atap shelter",
    tempat_duduk: "Tempat duduk",
    papan_informasi_rute: "Papan informasi rute",
    jalur_landai_difabel: "Jalur landai difabel",
    penerangan: "Penerangan",
    dinding_kaca_pembatas: "Dinding kaca pembatas",
    kipas_angin: "Kipas angin",
    papan_nama: "Papan nama jelas",
};

const DAMAGE_LABELS: Record<string, string> = {
    rusak_robek: "Rusak / robek",
    vandalisme: "Coret vandalisme",
    karat_mengelupas: "Karat mengelupas",
    kotor_debu_sampah: "Kotor / debu / sampah",
    akses_terhalang: "Akses terhalang",
};

function pickNumber(detail: BusStopDetail, keys: (keyof BusStopDetail)[]): number | null {
    for (const key of keys) {
        const value = detail[key];
        if (typeof value === "number") return value;
    }
    return null;
}

export default function BusStopPanel({ sourceId, onClose }: { sourceId: string | null; onClose: () => void }) {
    if (!sourceId) return null;
    return <BusStopDetailPanel key={sourceId} sourceId={sourceId} onClose={onClose} />;
}

function BusStopDetailPanel({ sourceId, onClose }: { sourceId: string; onClose: () => void }) {
    const [detail, setDetail] = useState<BusStopDetail | null>(null);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let mounted = true;
        fetchBusStopDetail(sourceId)
            .then((value) => mounted && setDetail(value))
            .catch((err) => mounted && setError(err instanceof Error ? err : new Error("Data halte tidak tersedia")));
        return () => {
            mounted = false;
        };
    }, [sourceId]);

    // Low intervention score = poor condition = priority (red); high = healthy (green).
    const badgeColor = interventionColor(detail?.intervention_score);
    const badgeText = readableTextOn(badgeColor);
    const photos = (detail?.media ?? []).filter((item) => item?.url);
    const damageList = Object.entries(detail?.damage_indicators ?? {})
        .filter(([, flagged]) => flagged)
        .map(([key]) => key);

    return (
        <aside className={PANEL_CLASS}>
            <div className={SEGMENT_PANEL_HEADER_CLASS}>
                <div className={`${PANEL_ICON_CLASS} flex-[0_0_auto]`}><Bus aria-hidden="true" /></div>
                <div className={SEGMENT_PANEL_TITLE_CLASS}>
                    <span>HALTE SURVEI</span>
                    <h2>{detail?.title ?? sourceId}</h2>
                </div>
                <button onClick={onClose} className={`${PANEL_CLOSE_CLASS} m-0 bg-[#0b1a2a]`} aria-label="Tutup panel halte"><X aria-hidden="true" /></button>
            </div>
            <div className={SEGMENT_PANEL_CONTENT_CLASS}>
                {!detail && !error && <div className={SEGMENT_OVERVIEW_CLASS}><Skeleton height={16} width="62%" /><Skeleton height={14} width="28%" /></div>}
                {error && <div className={`${SEGMENT_STATE_CLASS} [&>strong]:text-[#f87171]`}><strong>Data halte tidak tersedia</strong><span>{error.message}</span></div>}
                {detail && (
                    <>
                        <div className={SEGMENT_OVERVIEW_CLASS}>
                            <strong>{detail.intervention_class ?? "Belum dinilai"}</strong>
                            <span>{detail.intervention_rank == null ? "Peringkat belum tersedia" : `Peringkat intervensi ${fmtIntId(detail.intervention_rank)}`}</span>
                            <b className="col-span-full mt-[3px] inline-flex w-max items-center rounded-[5px] px-[7px] py-1 text-[8px] font-extrabold tracking-[0.06em] uppercase" style={{ background: badgeColor, color: badgeText }}>{detail.intervention_class ?? "-"}</b>
                        </div>
                        <AutoInsightCard entity={{ type: "stop", id: sourceId }} label={detail.title ?? sourceId} />
                        <section className={SEGMENT_SECTION_CLASS}>
                            <SectionTitle title="Skor komponen" meta={`Skor intervensi ${detail.intervention_score == null ? MISSING_LABEL : fmtFloatId(detail.intervention_score, 3)}`} />
                            <div className={`${STAT_GRID_CLASS} gap-[9px]`}>
                                {COMPONENTS.map(({ keys, label }) => {
                                    const value = pickNumber(detail, keys);
                                    return (
                                        <div className={`${STAT_CARD_CLASS} flex min-h-[84px] min-w-0 flex-col justify-between border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.82)] p-3`} key={label}>
                                            <span className="text-[10px] font-extrabold leading-[1.2] tracking-[0.04em]">{label}</span>
                                            <strong className={`mt-[10px] block w-full text-right text-[clamp(13px,1.15vw,17px)] leading-[1.3] tracking-[-0.02em] text-[#f1f5f9] tabular-nums [overflow-wrap:anywhere] ${value == null ? DATA_MISSING_CLASS : ""}`}>{value == null ? MISSING_LABEL : fmtFloatId(value, 2)}</strong>
                                        </div>
                                    );
                                })}
                            </div>
                        </section>
                        {detail.facility_checklist && (
                            <section className={SEGMENT_SECTION_CLASS}>
                                <SectionTitle title="Checklist fasilitas (survei)" />
                                <div className={CRITERIA_GRID_CLASS}>
                                    {Object.entries(detail.facility_checklist).map(([key, present]) => (
                                        <div key={key}>
                                            <span>{FACILITY_LABELS[key] ?? key}</span>
                                            <strong className={present ? "" : DATA_MISSING_CLASS}>{present ? "Ada" : "Tidak"}</strong>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}
                        {detail.damage_indicators && (
                            <section className={SEGMENT_SECTION_CLASS}>
                                <SectionTitle title="Indikator kerusakan" />
                                {damageList.length === 0 && <p className={SEGMENT_EMPTY_CLASS}>Tidak ada indikator kerusakan terdeteksi</p>}
                                {damageList.map((key) => (
                                    <p className="mt-[10px] mb-0 rounded-[0_6px_6px_0] border-l-2 border-[rgba(245,165,36,0.42)] bg-[rgba(245,165,36,0.055)] px-[10px] py-[9px] text-[10px] leading-[1.5] text-[#8292a8]" key={key}>- {DAMAGE_LABELS[key] ?? key}</p>
                                ))}
                            </section>
                        )}
                        <section className={SEGMENT_SECTION_CLASS}>
                            <SectionTitle title="POI sekitar" meta={`Dalam ${fmtIntId(detail.accessibility_buffer_m)} m`} />
                            {detail.accessibility_breakdown.length === 0 && <p className={SEGMENT_EMPTY_CLASS}>Tidak ada POI tercatat di sekitar halte</p>}
                            {detail.accessibility_breakdown.length > 0 && (
                                <div className={CRITERIA_GRID_CLASS}>
                                    {detail.accessibility_breakdown.map((item) => (
                                        <div key={item.category}><span>{item.category ?? "Tidak diketahui"}</span><strong>{fmtIntId(item.count)}</strong></div>
                                    ))}
                                </div>
                            )}
                        </section>
                        <section className={SEGMENT_SECTION_CLASS}>
                            <SectionTitle title="Observasi" meta={detail.observed_at ? fmtDateTimeId(detail.observed_at) : MISSING_LABEL} />
                            {detail.observer_name && <p className="mt-[10px] mb-0 rounded-[0_6px_6px_0] border-l-2 border-[rgba(245,165,36,0.42)] bg-[rgba(245,165,36,0.055)] px-[10px] py-[9px] text-[10px] leading-[1.5] text-[#8292a8]">Pengamat: {detail.observer_name}</p>}
                            {detail.description && <p className="mt-[10px] mb-0 rounded-[0_6px_6px_0] border-l-2 border-[rgba(245,165,36,0.42)] bg-[rgba(245,165,36,0.055)] px-[10px] py-[9px] text-[10px] leading-[1.5] text-[#8292a8]">{detail.description}</p>}
                            {!detail.description && !detail.observer_name && <p className={SEGMENT_EMPTY_CLASS}>{MISSING_LABEL}</p>}
                        </section>
                        {photos.length > 0 && (
                            <section className={SEGMENT_SECTION_CLASS}>
                                <SectionTitle title="Foto" meta={`${photos.length} media`} />
                                <div className={CRITERIA_GRID_CLASS}>
                                    {photos.map((item, index) => (
                                        // eslint-disable-next-line @next/next/no-img-element
                                        <img className="w-full rounded-lg" key={index} src={item.url} alt={`${detail.title} ${index + 1}`} />
                                    ))}
                                </div>
                            </section>
                        )}
                    </>
                )}
            </div>
        </aside>
    );
}
