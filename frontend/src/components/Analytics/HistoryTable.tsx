"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, Search, SlidersHorizontal, X } from "lucide-react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchEmissionHistory } from "@/services/api";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fmtDateTimeId, fmtFloatId, fmtIntId } from "@/utils/format";
import EmissionBulkDelete from "./EmissionBulkDelete";
import EmissionExport from "./EmissionExport";
import HistoryFilterDrawer, { type HistoryFilters } from "./HistoryFilterDrawer";
import SectionTitle from "@/components/ui/SectionTitle";
import { SkeletonRows } from "@/components/ui/Skeleton";
import Select from "@/components/ui/Select";
import type { AnalyticsQuery, EmissionHistoryRecord, VehicleRates } from "@/types";

type SortKey = "period_start" | "segment_name";
type Tab = "observed" | "estimated";
const TABS: { key: Tab; label: string }[] = [{ key: "observed", label: "Terukur" }, { key: "estimated", label: "Estimasi" }];
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
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
    const { query, filter, setFilter, refresh } = useEmissionAnalytics();
    const [tab, setTab] = useState<Tab>("observed");
    const [searchInput, setSearchInput] = useState("");
    const [search, setSearch] = useState("");
    const [sourceMode, setSourceMode] = useState<string | null>(null);
    const [pageSize, setPageSize] = useState(25);
    const [sort, setSort] = useState<SortKey>("period_start");
    const [order, setOrder] = useState<"asc" | "desc">("desc");
    const [pages, setPages] = useState<{ key: string; values: Record<Tab, number> }>({ key: "", values: { observed: 1, estimated: 1 } });
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [reload, setReload] = useState(0);
    const [expanded, setExpanded] = useState<string | null>(null);

    useEffect(() => {
        const timer = setTimeout(() => setSearch(searchInput.trim()), 300);
        return () => clearTimeout(timer);
    }, [searchInput]);

    const sourceKey = JSON.stringify({ query, search, sourceMode, pageSize, sort, order });
    const sourceQuery: AnalyticsQuery = useMemo(() => ({
        ...query,
        ...(search ? { search } : {}),
        ...(sourceMode ? { source_mode: sourceMode } : {}),
    }), [query, search, sourceMode]);
    const effectiveQuery: AnalyticsQuery = useMemo(() => ({ ...sourceQuery, quality_status: tab }), [sourceQuery, tab]);

    // Totals are learned from each response so a tab's page can be clamped to
    // its own page count. Set from the fetch promise (not an effect) to keep the
    // render pure; pages are keyed to sourceKey, so any shared input change
    // derives page 1 while switching tabs keeps each tab's own page.
    const [totals, setTotals] = useState<Record<Tab, number>>({ observed: 0, estimated: 0 });
    const tabPages = pages.key === sourceKey ? pages.values : { observed: 1, estimated: 1 };
    const knownPages = Math.max(1, Math.ceil((totals[tab] || 1) / pageSize));
    const requestedPage = Math.min(tabPages[tab], knownPages);
    const load = useCallback((signal: AbortSignal) =>
        fetchEmissionHistory(effectiveQuery, { page: requestedPage, pageSize, sort, order, signal })
            .then((response) => {
                setTotals((current) => (current[tab] === response.total ? current : { ...current, [tab]: response.total }));
                return response;
            }),
        [effectiveQuery, requestedPage, pageSize, sort, order, tab]);
    const resourceKey = `${sourceKey}:${tab}:${requestedPage}:${reload}`;
    const { data, loading, error, key } = useAnalyticsResource(resourceKey, load);
    const view = key === resourceKey ? data : undefined;
    const totalPages = Math.max(1, Math.ceil((view?.total ?? 0) / pageSize));
    const page = view ? Math.min(requestedPage, totalPages) : requestedPage;

    const goPage = useCallback((next: number) => {
        setPages((current) => {
            const values = current.key === sourceKey ? current.values : { observed: 1, estimated: 1 };
            return { key: sourceKey, values: { ...values, [tab]: next } };
        });
        setExpanded(null);
    }, [tab, sourceKey]);

    function changeSort(next: SortKey) {
        setOrder(sort === next ? (order === "asc" ? "desc" : "asc") : next === "period_start" ? "desc" : "asc");
        setSort(next);
        setExpanded(null);
    }
    function switchTab(next: Tab) { setTab(next); setExpanded(null); }
    function handleDeleted() {
        setPages({ key: sourceKey, values: { observed: 1, estimated: 1 } });
        setReload((value) => value + 1);
        refresh();
        setExpanded(null);
    }
    const closeDrawer = useCallback(() => setDrawerOpen(false), []);
    const applyFilters = useCallback((next: HistoryFilters) => {
        setFilter({ corridorId: next.corridorId, segmentId: next.segmentId, from: next.from, to: next.to });
        setSourceMode(next.sourceMode);
        setDrawerOpen(false);
    }, [setFilter]);

    const appliedFilters: HistoryFilters = {
        corridorId: filter.corridorId, segmentId: filter.segmentId, sourceMode,
        from: filter.from, to: filter.to,
    };
    const activeFilterCount = [filter.corridorId, filter.segmentId, sourceMode, filter.from || filter.to].filter(Boolean).length;

    function sortHeader(label: string, sortKey: SortKey) {
        const active = sort === sortKey;
        return <button type="button" className={`history-sort${active ? " is-active" : ""}`} onClick={() => changeSort(sortKey)}>
            {label}<span aria-hidden="true">{active ? (order === "asc" ? "▲" : "▼") : "↕"}</span>
        </button>;
    }

    return <section className="page-card history-card animate-in" aria-label="Riwayat emisi segmen" aria-busy={loading}>
        <SectionTitle title="Riwayat perhitungan segmen" meta={`Laju polutan dalam ${view?.units.emissions ?? data?.units.emissions ?? "kg/hour"}; hasil sintetis dan replay dikecualikan.`} aside={`${fmtIntId(view?.total ?? 0)} catatan`} />

        <div className="history-toolbar">
            <div className="history-tabs" role="tablist" aria-label="Status mutu data">
                {TABS.map(({ key: tabKey, label }) => <button key={tabKey} type="button" role="tab" aria-selected={tab === tabKey}
                    className={`history-tab${tab === tabKey ? " is-active" : ""}`} onClick={() => switchTab(tabKey)}>{label}</button>)}
            </div>
            <label className="history-search">
                <Search aria-hidden="true" />
                <input type="search" value={searchInput} aria-label="Cari riwayat"
                    placeholder="Cari nama jalan, segmen, atau informasi lain"
                    onChange={(event) => setSearchInput(event.target.value)} />
                {searchInput && <button type="button" aria-label="Bersihkan pencarian" onClick={() => setSearchInput("")}><X aria-hidden="true" /></button>}
            </label>
            <button type="button" className="analytics-button history-filter-button" aria-haspopup="dialog" onClick={() => setDrawerOpen(true)}>
                <SlidersHorizontal aria-hidden="true" /> Filter
                {activeFilterCount > 0 && <span className="history-filter-count" aria-label={`${activeFilterCount} filter aktif`}>{activeFilterCount}</span>}
            </button>
        </div>

        <EmissionExport query={effectiveQuery} />
        <EmissionBulkDelete query={effectiveQuery} page={page} pageSize={pageSize} totalPages={totalPages} sort={sort} order={order} onDeleted={handleDeleted} />

        {!view && loading ? <SkeletonRows rows={6} height={54} />
            : !view && error ? <p role="alert" className="analytics-error">{error}</p>
            : !view?.data.length ? <div className="unavailable-state">Tidak ada pengamatan segmen pada rentang dan lokasi ini.</div>
            : <div className="table-wrap history-scroll">
                <table className="priority-table history-table">
                    <thead><tr>
                        <th className="history-index center">No</th>
                        <th>{sortHeader("Waktu", "period_start")}</th>
                        <th>{sortHeader("Lokasi", "segment_name")}</th>
                        <th>Kendaraan / jam</th>
                        <th className="history-num">Total emisi</th>
                        <th>Status</th>
                        <th aria-label="Detail" />
                    </tr></thead>
                    <tbody>{view.data.map((record, index) => {
                        const open = expanded === record.id;
                        const no = (page - 1) * pageSize + index + 1;
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

        <nav className="analytics-pagination history-pagination" aria-label="Navigasi halaman riwayat">
            <div className="history-pagination-left">
                <span>Menampilkan {fmtIntId(view?.data.length ?? 0)} dari {fmtIntId(view?.total ?? 0)} catatan</span>
                <label className="history-pagesize">Baris per halaman
                    <Select ariaLabel="Jumlah baris per halaman" value={String(pageSize)}
                        options={PAGE_SIZE_OPTIONS.map((size) => ({ value: String(size), label: String(size) }))}
                        onChange={(value) => setPageSize(Number(value))} />
                </label>
            </div>
            <div className="history-pagination-right">
                <span>{page} dari {totalPages} halaman</span>
                <button type="button" className="pagination-page" aria-label="Halaman sebelumnya"
                    disabled={loading || page <= 1} onClick={() => goPage(page - 1)}><ChevronLeft aria-hidden="true" /></button>
                <button type="button" className="pagination-page" aria-label="Halaman berikutnya"
                    disabled={loading || !view || page >= totalPages} onClick={() => goPage(page + 1)}><ChevronRight aria-hidden="true" /></button>
            </div>
        </nav>

        <HistoryFilterDrawer open={drawerOpen} filters={appliedFilters} onClose={closeDrawer} onApply={applyFilters} />
    </section>;
}
