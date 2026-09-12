"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Search, SlidersHorizontal, X } from "lucide-react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchEmissionHistory } from "@/services/api";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fmtDateTimeId, fmtFloatId, fmtIntId, formatCalculationMode, formatCameraName, formatSemantics, formatSourceMode } from "@/utils/format";
import EmissionBulkDelete from "./EmissionBulkDelete";
import EmissionExport from "./EmissionExport";
import HistoryFilterDrawer, { type HistoryFilters } from "./HistoryFilterDrawer";
import HistoryPagination from "./HistoryPagination";
import SectionTitle from "@/components/ui/SectionTitle";
import { SkeletonRows } from "@/components/ui/Skeleton";
import type { AnalyticsQuery, EmissionHistoryRecord, VehicleRates } from "@/types";
import { ANALYTICS_BUTTON_CLASS, ANALYTICS_ERROR_CLASS, ANIMATE_IN_CLASS, PAGE_CARD_CLASS, PRIORITY_TABLE_CLASS, TABLE_WRAP_CLASS, UNAVAILABLE_STATE_CLASS } from "@/styles/tailwind";

type SortKey = "period_start" | "segment_name";
type Tab = "observed" | "estimated";
const TABS: { key: Tab; label: string }[] = [{ key: "observed", label: "Terukur" }, { key: "estimated", label: "Perkiraan" }];
const VEHICLES: { key: keyof VehicleRates; label: string }[] = [
    { key: "car", label: "Mobil" }, { key: "motorcycle", label: "Motor" },
    { key: "bus", label: "Bus" }, { key: "truck", label: "Truk" },
];
function StatusBadge({ record }: { record: EmissionHistoryRecord }) {
    const label = record.is_interpolated ? "Perkiraan jam" : record.quality_status === "estimated" ? "Perkiraan" : "Terukur";
    const qualityClass = record.is_interpolated ? "bg-[#334155] text-[#cbd5e1]" : record.quality_status === "estimated" ? "bg-[rgba(245,165,36,0.12)] text-[#fbbf24]" : "bg-[rgba(34,197,94,0.12)] text-[#4ade80]";
    return <div className="flex flex-col gap-1">
        <span className={`inline-block w-fit rounded-full px-2 py-0.75 text-[9px] font-(--weight-strong) ${qualityClass}`}>{label}</span>
        <small className="text-[9px] text-(--muted)">{formatSourceMode(record.source_mode)} · {record.freshness_status === "fresh" ? "segar" : "perlu diperbarui"}</small>
    </div>;
}

function VehicleBreakdown({ volume }: { volume: VehicleRates | null }) {
    if (!volume) return <span className="text-[9px] text-(--muted)">Tidak tersedia</span>;
    return <span className="mt-1.25 flex flex-wrap gap-x-2.5 gap-y-0.75 text-[9px] text-(--secondary)">{VEHICLES.map(({ key, label }) => <span key={key}>{label} {fmtIntId(volume[key])}</span>)}</span>;
}

function DetailPanel({ record }: { record: EmissionHistoryRecord }) {
    const groupClass = "[&_h4]:mt-0 [&_h4]:mb-2.25 [&_h4]:text-[9px] [&_h4]:font-(--weight-strong) [&_h4]:tracking-widest [&_h4]:text-(--secondary) [&_h4]:uppercase [&_h4:not(:first-child)]:mt-4 [&_dl]:m-0 [&_dl]:grid [&_dl]:gap-1.5 [&_dl>div]:flex [&_dl>div]:items-center [&_dl>div]:justify-between [&_dl>div]:gap-3 [&_dl>div]:text-[11px] [&_dt]:inline-flex [&_dt]:items-center [&_dt]:gap-1.5 [&_dt]:text-(--secondary) [&_dt_i]:h-2 [&_dt_i]:w-2 [&_dt_i]:rounded-full [&_dd]:m-0 [&_dd]:text-right [&_dd]:text-(--text) [&_dd]:tabular-nums";
    return <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4.5 rounded-md border border-(--border) bg-(--card-2) p-3.5">
        <div className={groupClass}>
            <h4>Laju polutan · {record.units.emissions}</h4>
            <dl>{EMISSION_DEFINITIONS.map((p) => <div key={p.key}><dt><i style={{ background: p.color }} />{p.label}</dt><dd>{record.emissions_kg_h[p.key] == null ? "-" : fmtFloatId(record.emissions_kg_h[p.key], 6)}</dd></div>)}</dl>
        </div>
        <div className={groupClass}>
            <h4>Volume kendaraan · {record.units.volume_per_hour}</h4>
            <dl>{VEHICLES.map(({ key, label }) => <div key={key}><dt>{label}</dt><dd>{record.volume_per_hour ? fmtIntId(record.volume_per_hour[key]) : "-"}</dd></div>)}</dl>
            <h4>VKT · {record.units.vkt_km_h}</h4>
            <dl>{VEHICLES.map(({ key, label }) => <div key={key}><dt>{label}</dt><dd>{record.detail.vkt_km_h ? fmtFloatId(record.detail.vkt_km_h[key], 2) : "-"}</dd></div>)}</dl>
        </div>
        <div className={groupClass}>
            <h4>Sumber data</h4>
            <dl>
                <div><dt>Periode</dt><dd>{fmtDateTimeId(record.period_start)} – {fmtDateTimeId(record.period_end)}</dd></div>
                <div><dt>Metode hitung</dt><dd>{formatCalculationMode(record.detail.calculation_mode)}</dd></div>
                <div><dt>Jenis hitungan</dt><dd>{formatSemantics(record.vehicle_count_semantics)}</dd></div>
                <div><dt>Kamera</dt><dd>{record.detail.source_cameras.map(formatCameraName).join(", ") || "Tidak tercatat"}</dd></div>
                <div><dt>Stream</dt><dd>{record.detail.source_streams.join(", ") || "Tidak tercatat"}</dd></div>
                <div><dt>Observasi</dt><dd>{fmtIntId(record.detail.source_observation_count)} · {fmtFloatId(record.detail.observation_duration_seconds, 1)} detik</dd></div>
            </dl>
        </div>
    </div>;
}

export default function HistoryTable() {
    const { query, filter, setFilter, refresh } = useEmissionAnalytics();
    const [tab, setTab] = useState<Tab>("estimated");
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
    const tabRefs = useRef<Partial<Record<Tab, HTMLButtonElement | null>>>({});

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
    function moveTab(event: React.KeyboardEvent<HTMLButtonElement>, current: Tab) {
        const index = TABS.findIndex(({ key }) => key === current);
        let next = index;
        if (event.key === "ArrowRight") next = (index + 1) % TABS.length;
        else if (event.key === "ArrowLeft") next = (index - 1 + TABS.length) % TABS.length;
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = TABS.length - 1;
        else return;
        event.preventDefault();
        const nextTab = TABS[next].key;
        switchTab(nextTab);
        tabRefs.current[nextTab]?.focus();
    }
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
        return <button type="button" className={`inline-flex w-full cursor-pointer items-center gap-1.5 border-0 bg-transparent px-2.5 py-2.25 text-[8px] font-(--weight-strong) tracking-[0.08em] uppercase hover:text-(--text) [&>span]:text-[9px] ${active ? "text-(--green)" : "text-(--muted)"}`} onClick={() => changeSort(sortKey)}>
            {label}<span aria-hidden="true">{active ? (order === "asc" ? "▲" : "▼") : "↕"}</span>
        </button>;
    }

    return <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-label="Riwayat emisi segmen" aria-busy={loading}>
        <SectionTitle title="Riwayat perhitungan segmen" meta={`Laju polutan dalam ${view?.units.emissions ?? data?.units.emissions ?? "kg/hour"}; profil historis segmen dirender per jam pada hari terpilih, jam terisi ditandai.`} aside={`${fmtIntId(view?.total ?? 0)} catatan`} />

        <div className="mt-3.5 mb-1 flex flex-wrap items-center gap-3">
            <div className="inline-flex gap-0.75 rounded-full border border-(--border) bg-(--card-2) p-0.75" role="tablist" aria-label="Status mutu data">
                {TABS.map(({ key: tabKey, label }) => <button key={tabKey} ref={(node) => { tabRefs.current[tabKey] = node; }} type="button" role="tab" aria-selected={tab === tabKey} tabIndex={tab === tabKey ? 0 : -1}
                    className={`min-h-9 cursor-pointer rounded-full border-0 bg-transparent px-4 py-1.5 text-xs font-semibold hover:text-(--text) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--green) max-[760px]:min-h-11 ${tab === tabKey ? "bg-[#102238]! text-[#4ade80]!" : "text-(--secondary)"}`} onClick={() => switchTab(tabKey)} onKeyDown={(event) => moveTab(event, tabKey)}>{label}</button>)}
            </div>
            <label className="relative flex h-(--control-height) min-w-55 flex-[1_1_260px] items-center gap-2 rounded-sm border border-[#334155] bg-[#102238] px-3 text-(--muted) [&>svg]:h-3.75 [&>svg]:w-3.75 [&>svg]:shrink-0">
                <Search aria-hidden="true" />
                <input className="min-w-0 flex-1 border-0 bg-transparent text-xs text-[#edf5ff] outline-none placeholder:text-[#64748b]" type="search" value={searchInput} aria-label="Cari riwayat"
                    placeholder="Cari nama jalan, segmen, atau informasi lain"
                    onChange={(event) => setSearchInput(event.target.value)} />
                {searchInput && <button className="grid h-5.5 w-5.5 cursor-pointer place-items-center rounded-full border-0 bg-transparent text-(--muted) hover:text-(--text) [&>svg]:h-3.5 [&>svg]:w-3.5" type="button" aria-label="Bersihkan pencarian" onClick={() => setSearchInput("")}><X aria-hidden="true" /></button>}
            </label>
            <button type="button" className={`${ANALYTICS_BUTTON_CLASS} inline-flex items-center gap-1.75 [&>svg]:h-3.75 [&>svg]:w-3.75`} aria-haspopup="dialog" onClick={() => setDrawerOpen(true)}>
                <SlidersHorizontal aria-hidden="true" /> Filter
                {activeFilterCount > 0 && <span className="inline-grid h-4.5 min-w-4.5 place-items-center rounded-full bg-(--green) px-1.25 text-[10px] font-bold text-[#062018]" aria-label={`${activeFilterCount} filter aktif`}>{activeFilterCount}</span>}
            </button>
        </div>

        <EmissionExport query={effectiveQuery} />
        <EmissionBulkDelete query={effectiveQuery} page={page} pageSize={pageSize} totalPages={totalPages} sort={sort} order={order} onDeleted={handleDeleted} />

        {!view && loading ? <SkeletonRows rows={6} height={54} />
            : !view && error ? <p role="alert" className={ANALYTICS_ERROR_CLASS}>{error}</p>
            : !view?.data.length ? <div className={UNAVAILABLE_STATE_CLASS}>Tidak ada pengamatan segmen pada rentang dan lokasi ini.</div>
            : <div className={`${TABLE_WRAP_CLASS} max-h-155 overflow-auto rounded-md border border-(--border)`}>
                <table className={`${PRIORITY_TABLE_CLASS} min-w-225 [&_th]:sticky [&_th]:top-0 [&_th]:z-2 [&_th]:bg-[#0e1d2e] [&_th]:p-0 [&_td]:px-2.5 [&_td]:py-3 [&_td]:align-top [&_small]:text-(--muted)`}>
                    <thead><tr>
                        <th className="w-11.5 text-right text-(--secondary) tabular-nums">No</th>
                        <th>{sortHeader("Waktu", "period_start")}</th>
                        <th>{sortHeader("Lokasi", "segment_name")}</th>
                        <th>Kendaraan / jam</th>
                        <th className="text-right tabular-nums">Total emisi</th>
                        <th>Status</th>
                        <th aria-label="Detail" />
                    </tr></thead>
                    <tbody>{view.data.map((record, index) => {
                        const open = expanded === record.id;
                        const no = (page - 1) * pageSize + index + 1;
                        return [
                            <tr key={record.id} className={open ? "[&>td]:bg-[#0e1d2e]" : ""}>
                                <td className="w-11.5 text-right text-(--secondary) tabular-nums">{no}</td>
                                <td><strong>{fmtDateTimeId(record.observed_at)}</strong><br /><small>{fmtDateTimeId(record.period_start)} – {fmtDateTimeId(record.period_end)}</small></td>
                                <td><strong>{record.segment_name}</strong><br /><small>{record.corridor_name}</small></td>
                                <td><strong>{record.total_vehicles_per_hour == null ? "-" : fmtIntId(record.total_vehicles_per_hour)}</strong><VehicleBreakdown volume={record.volume_per_hour} /></td>
                                <td className="text-right tabular-nums"><strong>{record.total_emissions_kg_h == null ? "-" : fmtFloatId(record.total_emissions_kg_h, 3)}</strong><br /><small>{record.units.emissions}</small></td>
                                <td><StatusBadge record={record} /></td>
                                <td><button type="button" className="grid h-10 w-10 cursor-pointer place-items-center rounded-sm border border-(--border) bg-(--card-2) text-(--secondary) transition-colors duration-150 hover:border-(--green) hover:text-(--text) [&>svg]:h-3.5 [&>svg]:w-3.5" aria-expanded={open} aria-label={open ? `Tutup detail ${record.segment_name}` : `Buka detail ${record.segment_name}`} onClick={() => setExpanded(open ? null : record.id)}>
                                    {open ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}</button></td>
                            </tr>,
                            open ? <tr key={`${record.id}-detail`}><td className="px-2.5! pt-0! pb-3.5!" colSpan={7}><DetailPanel record={record} /></td></tr> : null,
                        ];
                    })}</tbody>
                </table>
            </div>}

        <HistoryPagination displayedCount={view?.data.length ?? 0} total={view?.total ?? 0} pageSize={pageSize}
            onPageSizeChange={(size) => { setPageSize(size); setExpanded(null); }}
            page={page} totalPages={totalPages} onPageChange={goPage}
            loading={loading} hasData={!!view} />

        <HistoryFilterDrawer open={drawerOpen} filters={appliedFilters} onClose={closeDrawer} onApply={applyFilters} />
    </section>;
}
