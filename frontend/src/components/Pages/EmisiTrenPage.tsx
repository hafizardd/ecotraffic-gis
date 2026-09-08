"use client";
import { useEffect, useState } from "react";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchEmissionsSummary } from "@/services/api";
import { EmissionSummary } from "@/types";
import useMergedSegments from "@/hooks/useMergedSegments";
import { fmtDateTimeId, fmtEmissionId } from "@/utils/format";

export default function EmisiTrenPage() {
    const [summary, setSummary] = useState<EmissionSummary | null>(null);
    const { segments } = useMergedSegments();

    useEffect(() => {
        let mounted = true;
        fetchEmissionsSummary().then((v) => mounted && setSummary(v)).catch(() => {});
        return () => { mounted = false; };
    }, []);

    const top = [...segments]
        .sort((a, b) => (b.properties.decision_score ?? -1) - (a.properties.decision_score ?? -1))
        .slice(0, 8);

    return (
        <div className="page-container">
            <div className="page-header-section">
                <span>RINGKASAN</span>
                <h1>Emisi & Tren</h1>
                <p>
                    {summary?.last_updated
                        ? `Diperbarui ${fmtDateTimeId(summary.last_updated)} · ${String(summary.freshness_status ?? "unknown")}`
                        : "Ringkasan agregat kota dari kamera aktif."}
                </p>
            </div>
            <div className="page-card-grid">
                {EMISSION_DEFINITIONS.map(({ key, label, hourlyField }) => {
                    const v = summary?.[hourlyField] as number | undefined;
                    return (
                        <div className={`page-card summary-metric pollutant-${key}`} key={key}>
                            <span><i className="pollutant-dot" />{label}</span>
                            <strong>{v == null ? "Data tidak tersedia" : fmtEmissionId(Number(v), "kg/jam")}</strong>
                            <small>{summary ? "Agregat kota" : "Memuat..."}</small>
                        </div>
                    );
                })}
            </div>
            <div className="page-card">
                <div className="card-header">
                    <strong>Koridor prioritas</strong>
                    <span className="unavailable-badge">{top.length ? `${top.length} SEGMEN` : "BELUM TERSEDIA"}</span>
                </div>
                {top.length === 0 ? (
                    <div className="unavailable-state">Belum ada perhitungan emisi — data CCTV belum teragregasi.</div>
                ) : (
                    top.map((s) => (
                        <div key={s.properties.segment_id} className="ranking-row">
                            <strong>{s.properties.name}</strong>
                            <span>{s.properties.total_emission_g_h == null ? "Data tidak tersedia" : fmtEmissionId(Number(s.properties.total_emission_g_h))}</span>
                            <b className={`priority-badge priority-${s.properties.priority ?? "unknown"}`}>{s.properties.priority ?? "Belum dinilai"}</b>
                            <small>{String(s.properties.freshness_status ?? "unknown")}</small>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
