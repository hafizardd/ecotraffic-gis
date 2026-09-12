"use client";
import { useCallback, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Sector, Tooltip, XAxis, YAxis } from "recharts";
import type { PieSectorDataItem } from "recharts";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fetchEmissionTrend, fetchPollutantComposition, fetchTopEmissionCorridors } from "@/services/api";
import type { PollutantKey, TopEmissionCorridor } from "@/types";
import { fmtDateTimeId, fmtFloatId } from "@/utils/format";
import AnalyticsFilters from "../Analytics/AnalyticsFilters";
import RealtimePollutants from "../Analytics/RealtimePollutants";
import Checkbox from "@/components/ui/Checkbox";
import Select from "@/components/ui/Select";
import SectionTitle from "@/components/ui/SectionTitle";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { CHART_AXIS, CHART_GRID_STROKE, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE, entranceProps, useChartEntrance } from "@/components/charts/theme";
import { ANALYTICS_BUTTON_CLASS, ANALYTICS_CHART_GRID_CLASS, ANIMATE_IN_CLASS, CHART_CLASS, CHART_INTERACTIVE_CLASS, CHART_SMALL_CLASS, PAGE_CARD_CLASS, PAGE_CONTAINER_CLASS, PRIORITY_TABLE_CLASS, TABLE_WRAP_CLASS, UNAVAILABLE_STATE_CLASS } from "@/styles/tailwind";

const ALL_KEYS = EMISSION_DEFINITIONS.map((p) => p.key);
const DEFAULT_SELECTED = ALL_KEYS.filter((key) => key !== "co2");
const numericTooltip = (value: unknown) => typeof value === "number" ? `${fmtFloatId(value, 6)} kg/hour` : "Tidak tersedia";
const updateOverlay = (loading: boolean, hasData: boolean) => loading && hasData
    ? <div className="absolute top-1 right-1.5 inline-flex items-center gap-[var(--space-2)] rounded-full border border-[var(--border)] bg-[rgba(7,20,34,0.82)] px-[9px] py-1 text-[11px] text-[var(--secondary)]"><span className="h-3 w-3 animate-[spin_0.8s_linear_infinite] rounded-full border-[1.5px] border-[rgba(148,163,184,0.22)] border-t-[var(--green)]" />Memperbarui…</div> : null;
const renderActiveSector = ({ cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill }: PieSectorDataItem) => (
    <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={(outerRadius ?? 0) + 6} startAngle={startAngle} endAngle={endAngle} fill={fill} />
);

export default function EmisiTrenPage() {
    const { query, setFilter } = useEmissionAnalytics();
    const [selected, setSelected] = useState<PollutantKey[]>(DEFAULT_SELECTED);
    const [rankPollutant, setRankPollutant] = useState<PollutantKey>("co2");
    const load = useCallback(async (signal: AbortSignal) => {
        const [trend, top, composition] = await Promise.all([
            fetchEmissionTrend(query, signal), fetchTopEmissionCorridors(query, rankPollutant, signal), fetchPollutantComposition(query, signal),
        ]);
        return { trend, top, composition };
    }, [query, rankPollutant]);
    const { data, loading, error } = useAnalyticsResource(`${JSON.stringify(query)}:${rankPollutant}`, load);
    const rankingLabel = EMISSION_DEFINITIONS.find((p) => p.key === rankPollutant)?.label;
    const composition = data?.composition.data.filter((p) => selected.includes(p.key) && p.kg_h !== null && p.kg_h > 0) ?? [];
    const hasTrend = !!data?.trend.data.length, hasTop = !!data?.top.data.length, hasComposition = !!data?.composition.sample_count;
    const resolving = loading && !data;
    const status = error ?? "Tidak ada pengamatan segmen pada filter ini.";
    const trendEntrance = useChartEntrance(hasTrend);
    const topEntrance = useChartEntrance(hasTop);
    const pieEntrance = useChartEntrance(hasComposition);
    const emptyState = (message: string, alert = false) => <div className={UNAVAILABLE_STATE_CLASS} role={alert ? "alert" : "status"}>{message}</div>;
    function toggle(key: PollutantKey) { setSelected((values) => values.includes(key) ? values.filter((v) => v !== key) : [...values, key]); }
    const series = EMISSION_DEFINITIONS.filter((p) => selected.includes(p.key));
    function toggleFromLegend(value: unknown) {
        const def = EMISSION_DEFINITIONS.find((p) => p.label === value);
        if (def) toggle(def.key);
    }
    function selectCorridor(row: TopEmissionCorridor | undefined) {
        if (row?.corridor_id) setFilter({ corridorId: row.corridor_id, segmentId: null });
    }
    const topData = data?.top.data ?? [];
    return <div className={`${PAGE_CONTAINER_CLASS} [&_:focus-visible]:outline-2 [&_:focus-visible]:outline-offset-3 [&_:focus-visible]:outline-[#22c55e]`}>
        <SectionTitle page eyebrow="Analisis emisi" title="Emisi & Tren" meta="Laju delapan polutan dari pengamatan kendaraan pada segmen jalan." />
        <AnalyticsFilters />
        <RealtimePollutants />
        <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-busy={loading} aria-label="Tren emisi">
            <SectionTitle title="Tren emisi · kg/hour" meta="Rata-rata per segmen, dijumlahkan antarsegmen untuk polutan yang sama."
                aside={data?.trend.bucket ? `Per ${data.trend.bucket}` : undefined} />
            <div className="my-[14px] flex flex-wrap items-center gap-[var(--space-4)] text-xs">{EMISSION_DEFINITIONS.map((p) => <Checkbox key={p.key} checked={selected.includes(p.key)} onChange={() => toggle(p.key)} label={p.label} color={p.color} />)}
                <button className={ANALYTICS_BUTTON_CLASS} onClick={() => setSelected(ALL_KEYS)}>Semua</button>
                <button className={ANALYTICS_BUTTON_CLASS} onClick={() => setSelected(DEFAULT_SELECTED)}>Semua kecuali CO₂</button></div>
            <div className="relative">
                {resolving ? <ChartSkeleton height={320} />
                    : hasTrend && selected.length
                        ? <div className={`${CHART_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 800, height: 320 }}><LineChart data={data?.trend.data ?? []} margin={{ top: 20, right: 20, bottom: 12, left: 8 }} accessibilityLayer>
                            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} /><XAxis dataKey="timestamp" tickFormatter={(v: string) => new Date(v).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })} minTickGap={45} {...CHART_AXIS} /><YAxis width={76} {...CHART_AXIS} tickFormatter={(v: number) => fmtFloatId(v, 2)} />
                            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={numericTooltip} labelFormatter={(v) => fmtDateTimeId(String(v))} />
                            <Legend onClick={(entry) => toggleFromLegend((entry as { value?: string }).value)} />
                            {series.map((p, index) => <Line key={p.key} dataKey={`${p.key}_kg_h`} name={p.label} stroke={p.color} strokeWidth={2} dot={false} connectNulls={false} {...entranceProps(trendEntrance.active, index)} />)}
                        </LineChart></ResponsiveContainer></div>
                        : emptyState(resolving ? "Memuat analitik…" : hasTrend && !selected.length ? "Pilih polutan untuk ditampilkan." : status, !!error && !loading)}
                {updateOverlay(loading, hasTrend && !!selected.length)}
            </div>
        </section>
        <div className={ANALYTICS_CHART_GRID_CLASS}>
            <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-label="Lima koridor dengan emisi tertinggi" aria-busy={loading}>
                <SectionTitle title="Top 5 koridor" meta={`Diperingkat berdasarkan ${rankingLabel}. Klik batang untuk menyaring koridor.`}
                    aside={<Select ariaLabel="Polutan peringkat" value={rankPollutant}
                        options={EMISSION_DEFINITIONS.map((p) => ({ value: p.key, label: p.label }))} onChange={(value) => setRankPollutant(value as PollutantKey)} />} />
                <div className="relative">
                    {resolving ? <ChartSkeleton bars={5} height={250} />
                        : hasTop ? <>
                            <div className={`${CHART_CLASS} ${CHART_SMALL_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 600, height: 250 }}><BarChart data={topData} layout="vertical" margin={{ top: 8, right: 20, bottom: 8, left: 8 }} accessibilityLayer
                                onClick={(state) => selectCorridor((state as { activePayload?: { payload?: TopEmissionCorridor }[] } | undefined)?.activePayload?.[0]?.payload)}>
                                <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} /><XAxis type="number" {...CHART_AXIS} /><YAxis type="category" dataKey="corridor_name" width={125} {...CHART_AXIS} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={numericTooltip} /><Legend onClick={(entry) => toggleFromLegend((entry as { value?: string }).value)} />
                                {series.map((p, index) => <Bar key={p.key} dataKey={`${p.key}_kg_h`} name={p.label} fill={p.color} radius={[0, 3, 3, 0]} activeBar={{ stroke: "#f8fafc", strokeWidth: 1.5 }} {...entranceProps(topEntrance.active, index)} />)}
                            </BarChart></ResponsiveContainer></div>
                            <div className={TABLE_WRAP_CLASS}><table className={PRIORITY_TABLE_CLASS}><thead><tr><th>#</th><th>Koridor / segmen</th><th>kg/hour</th><th>Sampel</th><th>Teramati</th></tr></thead><tbody>{topData.map((row) => <tr key={row.corridor_id}><td>{row.rank}</td><td>{row.corridor_name}<br /><small>{row.segment_ids.join(", ")}{row.estimated_sample_count > 0 ? " · estimated" : ""}</small></td><td>{row.emission_kg_h == null ? "-" : fmtFloatId(row.emission_kg_h, 4)}</td><td>{row.sample_count}</td><td>{fmtDateTimeId(row.observed_at)}</td></tr>)}</tbody></table></div>
                        </> : emptyState(resolving ? "Memuat analitik…" : status, !!error && !loading)}
                    {updateOverlay(loading, hasTop)}
                </div>
            </section>
            <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS} [animation-delay:0.06s]`} aria-label="Komposisi polutan" aria-busy={loading}>
                <SectionTitle title="Komposisi laju massa" meta="Proporsi polutan terpilih pada periode ini." aside="kg/hour" />
                <div className="relative">
                    {resolving ? <ChartSkeleton bars={6} height={250} />
                        : hasComposition ? <>
                            {composition.length ? <div className={`${CHART_CLASS} ${CHART_SMALL_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 480, height: 250 }}><PieChart accessibilityLayer><Pie data={composition} dataKey="kg_h" nameKey="pollutant" innerRadius="52%" outerRadius="80%" paddingAngle={1} activeShape={renderActiveSector} {...entranceProps(pieEntrance.active)}>{composition.map((p) => <Cell key={p.key} fill={EMISSION_DEFINITIONS.find((d) => d.key === p.key)?.color} />)}</Pie><Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={numericTooltip} /></PieChart></ResponsiveContainer></div> : <div className={UNAVAILABLE_STATE_CLASS}>Tidak ada polutan terpilih yang bernilai.</div>}
                            <div className="grid grid-cols-2 gap-x-5 gap-y-[10px] max-[600px]:grid-cols-1">{data?.composition.data.map((p) => <div className="flex justify-between gap-2 text-xs" key={p.key}><button type="button" className="flex w-full cursor-pointer items-center justify-between gap-2 rounded-[5px] border-0 bg-transparent px-1 py-[3px] text-xs text-inherit hover:bg-[#102238] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--green)] aria-pressed:opacity-100 aria-[pressed=false]:opacity-45 [&_i]:mr-[7px] [&_i]:inline-block [&_i]:h-2 [&_i]:w-2 [&_i]:rounded-full" aria-pressed={selected.includes(p.key)} onClick={() => toggle(p.key)}><span><i style={{ background: EMISSION_DEFINITIONS.find((d) => d.key === p.key)?.color }} />{p.pollutant}</span><strong>{p.kg_h == null ? "-" : fmtFloatId(p.kg_h, 6)}</strong></button></div>)}</div>
                        </> : emptyState(resolving ? "Memuat analitik…" : status, !!error && !loading)}
                    {updateOverlay(loading, hasComposition)}
                </div>
            </section>
        </div>
    </div>;
}
