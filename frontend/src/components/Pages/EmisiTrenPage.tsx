"use client";
import { useCallback, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Sector, Tooltip, XAxis, YAxis } from "recharts";
import type { PieSectorDataItem } from "recharts";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fetchEmissionTrend, fetchPollutantComposition, fetchTopEmissionCorridors } from "@/services/api";
import type { PollutantKey, TopEmissionCorridor } from "@/types";
import { fmtChartTickId, fmtDateTimeId, fmtFloatId } from "@/utils/format";
import AnalyticsFilters from "../Analytics/AnalyticsFilters";
import RealtimePollutants from "../Analytics/RealtimePollutants";
import AnalyticsMeasureBand from "@/components/Analytics/AnalyticsMeasureBand";
import SeriesToggles from "@/components/Analytics/SeriesToggles";
import Select from "@/components/ui/Select";
import SectionTitle from "@/components/ui/SectionTitle";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { CHART_AXIS, CHART_GRID_STROKE, CHART_TOOLTIP_CURSOR, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE, entranceProps, useChartEntrance } from "@/components/charts/theme";
import { ANALYTICS_BUTTON_CLASS, ANALYTICS_CHART_GRID_CLASS, ANIMATE_IN_CLASS, CHART_CLASS, CHART_INTERACTIVE_CLASS, CHART_SMALL_CLASS, PAGE_CARD_CLASS, PAGE_CONTAINER_CLASS, PRIORITY_TABLE_CLASS, TABLE_WRAP_CLASS, UNAVAILABLE_STATE_CLASS } from "@/styles/tailwind";

const ALL_KEYS = EMISSION_DEFINITIONS.map((p) => p.key);
const DEFAULT_SELECTED = ALL_KEYS.filter((key) => key !== "co2");
const formatRate = (value: number) => fmtFloatId(value, Math.abs(value) < 0.01 ? 6 : Math.abs(value) < 1 ? 4 : 2);
const numericTooltip = (value: unknown) => typeof value === "number" ? `${formatRate(value)} kg/hour` : "Tidak tersedia";
const updateOverlay = (loading: boolean, hasData: boolean) => loading && hasData
    ? <div className="absolute top-1 right-1.5 inline-flex items-center gap-(--space-2) rounded-full border border-(--border) bg-[rgba(7,20,34,0.82)] px-[9px] py-1 text-[11px] text-(--secondary)"><span className="h-3 w-3 animate-[spin_0.8s_linear_infinite] rounded-full border-[1.5px] border-[rgba(148,163,184,0.22)] border-t-(--green)" />Memperbarui…</div> : null;
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
    const rankingColor = EMISSION_DEFINITIONS.find((p) => p.key === rankPollutant)?.color ?? "var(--brand)";
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
    function selectCorridor(row: TopEmissionCorridor | undefined) {
        if (row?.corridor_id) setFilter({ corridorId: row.corridor_id, segmentId: null });
    }
    const topData = data?.top.data ?? [];
    const selectedSet = new Set<string>(selected);
    const latestTrend = data?.trend.data.at(-1);
    const maxRankEmission = Math.max(0, ...topData.map((row) => row.emission_kg_h ?? 0));
    return <div className={`${PAGE_CONTAINER_CLASS} [&_:focus-visible]:outline-2 [&_:focus-visible]:outline-offset-3 [&_:focus-visible]:outline-[#22c55e]`}>
        <SectionTitle page eyebrow="Analisis emisi" title="Emisi & Tren" meta="Laju delapan polutan dari pengamatan kendaraan pada segmen jalan." />
        <AnalyticsFilters />
        <RealtimePollutants />
        <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-busy={loading} aria-label="Tren emisi">
            <SectionTitle title="Tren emisi · kg/hour" meta="Rata-rata per segmen, dijumlahkan antarsegmen untuk polutan yang sama."
                aside={data?.trend.bucket ? `Per ${data.trend.bucket}` : undefined} />
            <AnalyticsMeasureBand items={[
                { label: "Resolusi", value: data?.trend.bucket ?? "Menunggu data" },
                { label: "Titik seri", value: data?.trend.data.length ?? "–" },
                { label: "Segmen terbaru", value: latestTrend?.segment_count ?? "–" },
                { label: "Sampel terbaru", value: latestTrend?.sample_count ?? "–" },
                { label: "Estimasi", value: latestTrend?.estimated_sample_count ?? "–", tone: latestTrend?.estimated_sample_count ? "estimated" : "default" },
            ]} />
            <div className="mb-[14px] flex flex-wrap items-center gap-2 border-b border-(--border) pb-3 text-xs">
                <SeriesToggles items={EMISSION_DEFINITIONS.map((p) => ({ key: p.key, label: p.label, color: p.color }))} active={selectedSet} onToggle={(key) => toggle(key as PollutantKey)} label="Polutan yang ditampilkan" compact />
                <button className={ANALYTICS_BUTTON_CLASS} onClick={() => setSelected(ALL_KEYS)}>Semua</button>
                <button className={ANALYTICS_BUTTON_CLASS} onClick={() => setSelected(DEFAULT_SELECTED)}>Semua kecuali CO₂</button></div>
            <div className="relative">
                {resolving ? <ChartSkeleton height={320} />
                    : hasTrend && selected.length
                        ? <div className={`${CHART_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 800, height: 320 }}><LineChart data={data?.trend.data ?? []} margin={{ top: 20, right: 20, bottom: 12, left: 8 }} accessibilityLayer>
                            <CartesianGrid strokeDasharray="2 5" stroke={CHART_GRID_STROKE} vertical={false} /><XAxis dataKey="timestamp" tickFormatter={(v: string) => fmtChartTickId(v, query.from, query.to)} minTickGap={45} {...CHART_AXIS} /><YAxis width={68} {...CHART_AXIS} tickFormatter={(v: number) => formatRate(v)} />
                            <Tooltip cursor={CHART_TOOLTIP_CURSOR} contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={numericTooltip} labelFormatter={(v) => fmtDateTimeId(String(v))} />
                            {series.map((p, index) => <Line key={p.key} dataKey={`${p.key}_kg_h`} name={p.label} stroke={p.color} strokeWidth={2} dot={false} connectNulls={false} {...entranceProps(trendEntrance.active, index)} />)}
                        </LineChart></ResponsiveContainer></div>
                        : emptyState(resolving ? "Memuat analitik…" : hasTrend && !selected.length ? "Pilih polutan untuk ditampilkan." : status, !!error && !loading)}
                {updateOverlay(loading, hasTrend && !!selected.length)}
            </div>
        </section>
        <div className={ANALYTICS_CHART_GRID_CLASS}>
            <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-label="Lima koridor dengan emisi tertinggi" aria-busy={loading}>
                <SectionTitle title="Top 5 koridor" meta={`Diperingkat dan dibandingkan berdasarkan ${rankingLabel}. Klik batang untuk menyaring koridor.`}
                    aside={<Select ariaLabel="Polutan peringkat" value={rankPollutant}
                        options={EMISSION_DEFINITIONS.map((p) => ({ value: p.key, label: p.label }))} onChange={(value) => setRankPollutant(value as PollutantKey)} />} />
                <div className="relative">
                    {resolving ? <ChartSkeleton bars={5} height={250} />
                        : hasTop ? <>
                            <div className={`${CHART_CLASS} ${CHART_SMALL_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 600, height: 250 }}><BarChart data={topData} layout="vertical" margin={{ top: 8, right: 20, bottom: 8, left: 8 }} accessibilityLayer>
                                <CartesianGrid strokeDasharray="2 5" stroke={CHART_GRID_STROKE} horizontal={false} /><XAxis type="number" {...CHART_AXIS} tickFormatter={(value) => formatRate(Number(value))} /><YAxis type="category" dataKey="corridor_name" width={125} {...CHART_AXIS} />
                                <Tooltip cursor={{ fill: "var(--selection-soft)" }} contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={numericTooltip} />
                                <Bar dataKey="emission_kg_h" name={rankingLabel} fill={rankingColor} radius={[0, 3, 3, 0]} className="cursor-pointer" activeBar={{ stroke: "var(--text)", strokeWidth: 1.5 }} onClick={(row) => selectCorridor(row.payload as TopEmissionCorridor | undefined)} {...entranceProps(topEntrance.active)} />
                            </BarChart></ResponsiveContainer></div>
                            <div className={TABLE_WRAP_CLASS}><table className={PRIORITY_TABLE_CLASS}><thead><tr><th>#</th><th>Koridor / segmen</th><th>{rankingLabel} · kg/hour</th><th>Sampel</th><th>Teramati</th></tr></thead><tbody>{topData.map((row) => <tr key={row.corridor_id}><td>{row.rank}</td><td>{row.corridor_name}<br /><small>{row.segment_ids.join(", ")}{row.estimated_sample_count > 0 ? " · estimated" : ""}</small></td><td><div className="relative min-w-[106px] overflow-hidden rounded-(--radius-badge) bg-(--surface-sunken) px-2 py-1 text-right"><span className="absolute inset-y-0 left-0 opacity-20" style={{ width: `${maxRankEmission > 0 ? ((row.emission_kg_h ?? 0) / maxRankEmission) * 100 : 0}%`, backgroundColor: rankingColor }} aria-hidden="true" /><strong className="relative">{row.emission_kg_h == null ? "-" : formatRate(row.emission_kg_h)}</strong></div></td><td>{row.sample_count}</td><td>{fmtDateTimeId(row.observed_at)}</td></tr>)}</tbody></table></div>
                        </> : emptyState(resolving ? "Memuat analitik…" : status, !!error && !loading)}
                    {updateOverlay(loading, hasTop)}
                </div>
            </section>
            <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS} [animation-delay:0.06s]`} aria-label="Komposisi polutan" aria-busy={loading}>
                <SectionTitle title="Komposisi laju massa" meta="Proporsi polutan terpilih pada periode ini." aside="kg/hour" />
                <div className="relative">
                    {resolving ? <ChartSkeleton bars={6} height={250} />
                        : hasComposition ? <>
                            {composition.length ? <div className={`${CHART_CLASS} ${CHART_SMALL_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 480, height: 250 }}><PieChart accessibilityLayer><Pie data={composition} dataKey="kg_h" nameKey="pollutant" innerRadius="54%" outerRadius="80%" paddingAngle={1} stroke="var(--surface)" strokeWidth={1} activeShape={renderActiveSector} {...entranceProps(pieEntrance.active)}>{composition.map((p) => <Cell key={p.key} fill={EMISSION_DEFINITIONS.find((d) => d.key === p.key)?.color} />)}</Pie><Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={numericTooltip} /></PieChart></ResponsiveContainer></div> : <div className={UNAVAILABLE_STATE_CLASS}>Tidak ada polutan terpilih yang bernilai.</div>}
                            <div className="grid grid-cols-2 gap-x-5 gap-y-[7px] border-t border-(--border) pt-3 max-[600px]:grid-cols-1">{data?.composition.data.map((p) => <div className="flex justify-between gap-2 text-xs" key={p.key}><button type="button" className="flex w-full cursor-pointer items-center justify-between gap-2 rounded-[5px] border-0 bg-transparent px-1 py-[5px] text-xs text-inherit hover:bg-(--surface-raised) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--selection) aria-pressed:opacity-100 aria-[pressed=false]:opacity-45 [&_i]:mr-[7px] [&_i]:inline-block [&_i]:h-[3px] [&_i]:w-3" aria-pressed={selected.includes(p.key)} onClick={() => toggle(p.key)}><span><i style={{ background: EMISSION_DEFINITIONS.find((d) => d.key === p.key)?.color }} />{p.pollutant}</span><strong className="font-(family-name:--font-data) tabular-nums">{p.kg_h == null ? "-" : formatRate(p.kg_h)}</strong></button></div>)}</div>
                        </> : emptyState(resolving ? "Memuat analitik…" : status, !!error && !loading)}
                    {updateOverlay(loading, hasComposition)}
                </div>
            </section>
        </div>
    </div>;
}
