"use client";
import { useCallback, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchEmissionHistory } from "@/services/api";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fmtDateTimeId, fmtFloatId, fmtIntId } from "@/utils/format";
import EmissionExport from "./EmissionExport";
import SectionTitle from "@/components/ui/SectionTitle";
import { SkeletonRows } from "@/components/ui/Skeleton";
import type { EmissionHistoryRecord, VehicleRates } from "@/types";

type SortKey = "period_start" | "segment_name";
const PAGE_SIZE = 25;
const VEHICLES: { key: keyof VehicleRates; label: string }[] = [
    { key: "car", label: "Mobil" }, { key: "motorcycle", label: "Motor" },
    { key: "bus", label: "Bus" }, { key: "truck", label: "Truk" },
];
const SOURCE_LABELS: Record<string, string> = { LIVE: "Langsung", HISTORICAL: "Historis", SYNTHETIC: "Sintetis", REPLAY: "Replay", SNAPSHOT_REAL: "Snapshot" };

function StatusBadge({ record }: { record: EmissionHistoryRecord }) {
    return <div className="history-status">
        <span className={`history-badge quality-${record.quality_status}`}>{record.quality_status === "estimated" ? "Estimasi" : "Terukur"}</span>
        <small>{SOURCE_LABELS[record.source_mode] ?? record.source_mode} · {record.freshness_status === "fresh" ? "segar" : "basi"}</small>
    </div>;
}

function VehicleBreakdown({ volume }: { volume: VehicleRates | null }) {
    if (!volume) return <span className="history-muted">Tidak tersedia</span>;
    return <span className="history-vehicles">{VEHICLES.map(({ key, label }) => <span key={key}>{label} {fmtIntId(volume[key])}</span>)}</span>;
}

function DetailPanel({ record }: { record: EmissionHistoryRecord }) {
    return <div className="history-detail">
        <div className="history-detail-group">
            <h4>Laju polutan · {record.units.emissions}</h4>
            <dl>{EMISSION_DEFINITIONS.map((p) => <div key={p.key}><dt><i style={{ background: p.color }} />{p.label}</dt><dd>{record.emissions_kg_h[p.key] == null ? "—" : fmtFloatId(record.emissions_kg_h[p.key], 6)}</dd></div>)}</dl>
        </div>
        <div className="history-detail-group">
            <h4>Volume kendaraan · {record.units.volume_per_hour}</h4>
            <dl>{VEHICLES.map(({ key, label }) => <div key={key}><dt>{label}</dt><dd>{record.volume_per_hour ? fmtIntId(record.volume_per_hour[key]) : "—"}</dd></div>)}</dl>
            <h4>VKT · {record.units.vkt_km_h}</h4>
            <dl>{VEHICLES.map(({ key, label }) => <div key={key}><dt>{label}</dt><dd>{record.detail.vkt_km_h ? fmtFloatId(record.detail.vkt_km_h[key], 2) : "—"}</dd></div>)}</dl>
        </div>
        <div className="history-detail-group">
            <h4>Provenans</h4>
            <dl>
                <div><dt>Periode</dt><dd>{fmtDateTimeId(record.period_start)} – {fmtDateTimeId(record.period_end)}</dd></div>
                <div><dt>Metode hitung</dt><dd>{record.detail.calculation_mode} · v{record.detail.calculation_version}</dd></div>
                <div><dt>Semantik hitung</dt><dd>{record.vehicle_count_semantics}</dd></div>
                <div><dt>Kamera</dt><dd>{record.detail.source_cameras.join(", ") || "Tidak tercatat"}</dd></div>
                <div><dt>Stream</dt><dd>{record.detail.source_streams.join(", ") || "Tidak tercatat"}</dd></div>
                <div><dt>Observasi</dt><dd>{fmtIntId(record.detail.source_observation_count)} · {fmtFloatId(record.detail.observation_duration_seconds, 1)} detik</dd></div>
            </dl>
        </div>
    </div>;
}

export default function HistoryTable() {
    const { query } = useEmissionAnalytics();
    const queryKey = JSON.stringify(query);
    const [view, setView] = useState({ key: "", page: 1, sort: "period_start" as SortKey, order: "desc" as "asc" | "desc" });
    const [expanded, setExpanded] = useState<string | null>(null);
    const page = view.key === queryKey ? view.page : 1;
    const { sort, order } = view;
    const load = useCallback((signal: AbortSignal) => fetchEmissionHistory(query, page, sort, order, signal), [query, page, sort, order]);
    const { data, loading, error } = useAnalyticsResource(`${queryKey}:${page}:${sort}:${order}`, load);
    const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));

    function changeSort(next: SortKey) {
        setView((current) => {
            const key = current.key === queryKey ? current.key : queryKey;
            const direction = current.sort === next ? (current.order === "asc" ? "desc" : "asc") : next === "period_start" ? "desc" : "asc";
            return { key, page: 1, sort: next, order: direction };
        });
        setExpanded(null);
    }
    function goPage(next: number) { setView((current) => ({ ...current, key: queryKey, page: next })); setExpanded(null); }
    function sortHeader(label: string, key: SortKey) {
        const active = sort === key;
        return <button type="button" className={`history-sort${active ? " is-active" : ""}`} onClick={() => changeSort(key)}>
            {label}<span aria-hidden="true">{active ? (order === "asc" ? "▲" : "▼") : "↕"}</span>
        </button>;
    }

    return <section className="page-card history-card animate-in" aria-label="Riwayat emisi segmen" aria-busy={loading}>
        <SectionTitle title="Riwayat perhitungan segmen" meta={`Laju polutan dalam ${data?.units.emissions ?? "kg/hour"}; hasil sintetis dan replay dikecualikan.`} aside={`${fmtIntId(data?.total ?? 0)} catatan`} />
        <EmissionExport />
        {!data && loading ? <SkeletonRows rows={6} height={54} />
            : !data && error ? <p role="alert" className="analytics-error">{error}</p>
            : !data?.data.length ? <div className="unavailable-state">Tidak ada pengamatan segmen pada rentang dan lokasi ini.</div>
            : <div className="table-wrap history-scroll">
                <table className="priority-table history-table">
                    <thead><tr>
                        <th className="history-index">No</th>
                        <th>{sortHeader("Waktu", "period_start")}</th>
                        <th>{sortHeader("Lokasi", "segment_name")}</th>
                        <th>Kendaraan / jam</th>
                        <th className="history-num">Total emisi</th>
                        <th>Status</th>
                        <th aria-label="Detail" />
                    </tr></thead>
                    <tbody>{data.data.map((record, index) => {
                        const open = expanded === record.id;
                        const no = (page - 1) * PAGE_SIZE + index + 1;
                        return [
                            <tr key={record.id} className={open ? "is-open" : ""}>
                                <td className="history-index">{no}</td>
                                <td><strong>{fmtDateTimeId(record.observed_at)}</strong><br /><small>{fmtDateTimeId(record.period_start)} – {fmtDateTimeId(record.period_end)}</small></td>
                                <td><strong>{record.segment_name}</strong><br /><small>{record.corridor_name}</small></td>
                                <td><strong>{record.total_vehicles_per_hour == null ? "—" : fmtIntId(record.total_vehicles_per_hour)}</strong><VehicleBreakdown volume={record.volume_per_hour} /></td>
                                <td className="history-num"><strong>{record.total_emissions_kg_h == null ? "—" : fmtFloatId(record.total_emissions_kg_h, 3)}</strong><br /><small>{record.units.emissions}</small></td>
                                <td><StatusBadge record={record} /></td>
                                <td><button type="button" className="history-expand" aria-expanded={open} aria-label={open ? "Tutup detail" : "Buka detail"} onClick={() => setExpanded(open ? null : record.id)}>
                                    {open ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}</button></td>
                            </tr>,
                            open ? <tr key={`${record.id}-detail`} className="history-detail-row"><td colSpan={7}><DetailPanel record={record} /></td></tr> : null,
                        ];
                    })}</tbody>
                </table>
            </div>}
        <nav className="analytics-pagination" aria-label="Navigasi halaman riwayat">
            <button type="button" className="pagination-text" disabled={loading || page <= 1} onClick={() => goPage(page - 1)}>‹ Sebelumnya</button>
            <span className="pagination-status">Halaman {page} dari {totalPages}</span>
            <button type="button" className="pagination-text" disabled={loading || !data || page >= totalPages} onClick={() => goPage(page + 1)}>Berikutnya ›</button>
        </nav>
    </section>;
}
