"use client";
import { useEffect, useState } from "react";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchEmissionsSummary, fetchSegmentEmissionHistory, SegmentHistoryBucket } from "@/services/api";
import { EmissionSummary } from "@/types";
import useMergedSegments from "@/hooks/useMergedSegments";
import { fmtDateTimeId, fmtEmissionId, fmtFloatId, fmtIntId } from "@/utils/format";

export default function EmisiTrenPage() {
    const [summary, setSummary] = useState<EmissionSummary | null>(null);
    const [summaryStatus, setSummaryStatus] = useState<"loading" | "success" | "error">("loading");
    const [history, setHistory] = useState<SegmentHistoryBucket[]>([]);
    const [historyStatus, setHistoryStatus] = useState<"loading" | "success" | "error">("loading");
    const { segments, loading: segmentsLoading, error: segmentsError } = useMergedSegments();

    useEffect(() => {
        let mounted = true;

        const loadSummary = async () => {
            try {
                const value = await fetchEmissionsSummary();
                if (!mounted) return;
                setSummary(value);
                setSummaryStatus("success");
            } catch {
                if (mounted) setSummaryStatus("error");
            }
        };

        const loadHistory = async () => {
            try {
                const value = await fetchSegmentEmissionHistory();
                if (!mounted) return;
                setHistory(value.slice(-12));
                setHistoryStatus("success");
            } catch {
                if (mounted) setHistoryStatus("error");
            }
        };

        void loadSummary();
        void loadHistory();
        return () => { mounted = false; };
    }, []);

    const top = [...segments]
        .sort((a, b) => (b.properties.decision_score ?? -1) - (a.properties.decision_score ?? -1))
        .slice(0, 10);

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
            <div className="page-card-grid" aria-busy={summaryStatus === "loading"}>
                {EMISSION_DEFINITIONS.map(({ key, label, hourlyField }) => {
                    const value = summary?.[hourlyField];
                    const hasValue = typeof value === "number" && Number.isFinite(value);
                    const displayValue = summaryStatus === "loading"
                        ? "Memuat..."
                        : summaryStatus === "error"
                            ? "Gagal memuat data"
                            : hasValue
                                ? fmtEmissionId(value, "kg/jam")
                                : "Data tidak tersedia";
                    const statusLabel = summaryStatus === "loading"
                        ? "Menunggu ringkasan agregat kota"
                        : summaryStatus === "error"
                            ? "Ringkasan agregat kota gagal dimuat"
                            : hasValue
                                ? "Agregat kota"
                                : "Belum ada data agregat kota";
                    return (
                        <div className={`page-card summary-metric pollutant-${key}`} key={key}>
                            <span><i className="pollutant-dot" />{label}</span>
                            <strong>{displayValue}</strong>
                            <small>{statusLabel}</small>
                        </div>
                    );
                })}
            </div>
            <div className="page-card">
                <div className="card-header">
                    <strong>Tren per jam</strong>
                    <span className="unavailable-badge">
                        {historyStatus === "loading"
                            ? "MEMUAT..."
                            : historyStatus === "error"
                                ? "GAGAL DIMUAT"
                                : history.length
                                    ? `${history.length} BUCKET`
                                    : "BELUM TERSEDIA"}
                    </span>
                </div>
                {historyStatus === "loading" ? (
                    <div className="unavailable-state">Memuat tren emisi per jam...</div>
                ) : historyStatus === "error" ? (
                    <div className="unavailable-state">Gagal memuat tren emisi per jam.</div>
                ) : history.length === 0 ? (
                    <div className="unavailable-state">Belum ada perhitungan emisi — data CCTV belum teragregasi.</div>
                ) : (
                    <div className="trend-list">
                        {history.map((b) => (
                            <div key={`${b.segment_id}-${b.bucket_start}`} className="trend-row">
                                <span>{fmtDateTimeId(b.bucket_start)}</span>
                                <strong>{fmtEmissionId(b.avg_total_emission_g_h)}</strong>
                                <small>{fmtIntId(Math.round(b.avg_volume_per_hour))} kend/jam · {b.sample_count} sampel</small>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            <div className="page-card">
                <div className="card-header">
                    <strong>Koridor prioritas</strong>
                    <span className="unavailable-badge">
                        {segmentsLoading
                            ? "MEMUAT..."
                            : segmentsError
                                ? "GAGAL DIMUAT"
                                : top.length
                                    ? `${top.length} SEGMEN`
                                    : "BELUM TERSEDIA"}
                    </span>
                </div>
                {segmentsLoading ? (
                    <div className="unavailable-state">Memuat data koridor prioritas...</div>
                ) : segmentsError ? (
                    <div className="unavailable-state">Gagal memuat data koridor prioritas.</div>
                ) : top.length === 0 ? (
                    <div className="unavailable-state">Belum ada perhitungan emisi — data CCTV belum teragregasi.</div>
                ) : (
                    <div className="table-wrap">
                    <table className="priority-table">
                        <thead>
                            <tr>
                                <th>No</th>
                                <th>Nama Segmen</th>
                                <th>ID Segmen</th>
                                <th>Jumlah Emisi (g/jam)</th>
                                <th>Prioritas</th>
                                <th>Skor</th>
                                <th>Volume (kend/jam)</th>
                                <th>Diperbarui</th>
                            </tr>
                        </thead>
                        <tbody>
                            {top.map((s, i) => {
                                const vol = s.properties.volume_per_hour
                                    ? Object.values(s.properties.volume_per_hour).reduce((a, v) => a + Number(v), 0)
                                    : null;
                                return (
                                    <tr key={s.properties.segment_id}>
                                        <td>{fmtIntId(i + 1)}</td>
                                        <td>{s.properties.name}</td>
                                        <td>{s.properties.segment_id}</td>
                                        <td>{s.properties.total_emission_g_h == null ? "Data tidak tersedia" : fmtEmissionId(Number(s.properties.total_emission_g_h))}</td>
                                        <td><b className={`priority-badge priority-${s.properties.priority ?? "unknown"}`}>{s.properties.priority ?? "Belum dinilai"}</b></td>
                                        <td>{s.properties.decision_score == null ? "Data tidak tersedia" : fmtFloatId(Number(s.properties.decision_score), 2)}</td>
                                        <td>{vol == null ? "Data tidak tersedia" : fmtIntId(Math.round(vol))}</td>
                                        <td>{s.properties.calculated_at ? fmtDateTimeId(s.properties.calculated_at) : "Data tidak tersedia"}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                    </div>
                )}
            </div>
        </div>
    );
}
