"use client";
import { useCallback, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Sector, Tooltip, XAxis, YAxis } from "recharts";
import type { PieSectorDataItem } from "recharts";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fetchVehicleAnalytics } from "@/services/api";
import { fmtChartTickId, fmtDateTimeId, fmtFloatId, fmtIntId } from "@/utils/format";
import AnalyticsFilters from "../Analytics/AnalyticsFilters";
import AnalyticsMeasureBand from "@/components/Analytics/AnalyticsMeasureBand";
import AnalyticsMetricLedger from "@/components/Analytics/AnalyticsMetricLedger";
import SeriesToggles from "@/components/Analytics/SeriesToggles";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton, { ChartSkeleton, SkeletonRows } from "@/components/ui/Skeleton";
import { CHART_AXIS, CHART_GRID_STROKE, CHART_TOOLTIP_CURSOR, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE, entranceProps, useChartEntrance } from "@/components/charts/theme";
import type { VehicleKey } from "@/types";
import { ANALYTICS_CHART_GRID_CLASS, ANALYTICS_ERROR_CLASS, ANALYTICS_NOTE_CLASS, ANIMATE_IN_CLASS, CHART_CLASS, CHART_INTERACTIVE_CLASS, CHART_SMALL_CLASS, PAGE_CARD_CLASS, PAGE_CONTAINER_CLASS, PRIORITY_TABLE_CLASS, TABLE_WRAP_CLASS, UNAVAILABLE_STATE_CLASS } from "@/styles/tailwind";

const VEHICLES: { key: VehicleKey; rateKey: `${VehicleKey}_veh_h`; label: string; color: string }[] = [
    { key: "car", rateKey: "car_veh_h", label: "Mobil", color: "#38bdf8" },
    { key: "motorcycle", rateKey: "motorcycle_veh_h", label: "Motor", color: "#22c55e" },
    { key: "bus", rateKey: "bus_veh_h", label: "Bus", color: "#f5a524" },
    { key: "truck", rateKey: "truck_veh_h", label: "Truk", color: "#f05252" },
];

const vehicleTooltip = (value: unknown) => typeof value === "number" ? `${fmtIntId(value)} kend/jam` : "Tidak tersedia";
const num = (value: number | null | undefined) => (typeof value === "number" ? value : 0);
const renderActiveSector = ({ cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill }: PieSectorDataItem) => (
    <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={(outerRadius ?? 0) + 6} startAngle={startAngle} endAngle={endAngle} fill={fill} />
);

export default function KendaraanPage() {
    const { filter, query, setFilter } = useEmissionAnalytics();
    const [hidden, setHidden] = useState<Set<VehicleKey>>(() => new Set());
    const load = useCallback((signal: AbortSignal) => fetchVehicleAnalytics(query, signal), [query]);
    const { data, loading, error } = useAnalyticsResource(JSON.stringify(query), load);
    const resolving = loading && !data;
    const total = data?.total_vehicles_per_hour ?? null;
    const hasData = total != null && total > 0;
    const visible = VEHICLES.filter((vehicle) => !hidden.has(vehicle.key));
    const entrance = useChartEntrance(hasData);
    const compositionData = (data?.composition ?? [])
        .filter((slice) => !hidden.has(slice.key) && num(slice.vehicles_per_hour) > 0)
        .map((slice) => ({ name: VEHICLES.find((vehicle) => vehicle.key === slice.key)?.label ?? slice.key,
            value: num(slice.vehicles_per_hour), share: slice.share,
            fill: VEHICLES.find((vehicle) => vehicle.key === slice.key)?.color }));
    function toggle(key: VehicleKey) { setHidden((current) => { const next = new Set(current); if (next.has(key)) next.delete(key); else next.add(key); return next; }); }
    function filterSegment(segmentId: string) {
        // Toggle: clicking the focused segment again clears the focus.
        setFilter(filter.segmentId === segmentId ? { segmentId: null } : { segmentId, corridorId: null });
    }
    const activeVehicles = new Set<string>(visible.map((vehicle) => vehicle.key));
    const flowMetrics = [
        { key: "total", label: "Total arus", value: fmtIntId(total), unit: "kendaraan/jam", color: "var(--selection)", primary: true },
        ...VEHICLES.map((vehicle) => ({ key: vehicle.key, label: vehicle.label, value: fmtIntId(data?.totals[vehicle.key]), unit: "kendaraan/jam", color: vehicle.color })),
    ];
    const vktMetrics = [
        { key: "total-vkt", label: "Total VKT", value: fmtFloatId(data?.total_vkt_km_h, 1), unit: "km/jam", color: "var(--selection)", primary: true },
        ...VEHICLES.map((vehicle) => ({ key: `vkt-${vehicle.key}`, label: vehicle.label, value: fmtFloatId(data?.vkt[vehicle.key], 1), unit: "km/jam", color: vehicle.color })),
    ];
    const maxRankingTotal = Math.max(0, ...(data?.ranking ?? []).map((row) => row.total_veh_h ?? 0));

    return <div className={`${PAGE_CONTAINER_CLASS} [&_:focus-visible]:outline-2 [&_:focus-visible]:outline-offset-3 [&_:focus-visible]:outline-[#22c55e]`}>
        <SectionTitle page eyebrow="Analisis lalu lintas" title="Kendaraan" meta="Komposisi, peringkat segmen, VKT, dan tren volume kendaraan per jam." />
        <AnalyticsFilters />
        {error && !data ? <p role="alert" className={ANALYTICS_ERROR_CLASS}>{error}</p> : resolving ? <>
            <AnalyticsMetricLedger label="Ringkasan volume kendaraan" loading items={flowMetrics} />
            <div className={ANALYTICS_CHART_GRID_CLASS}>
                <section className={PAGE_CARD_CLASS}><Skeleton height={16} width="34%" /><div className="mt-3"><ChartSkeleton bars={6} height={220} /></div></section>
                <section className={PAGE_CARD_CLASS}><Skeleton height={16} width="45%" /><div className="mt-3"><ChartSkeleton bars={6} height={220} /></div></section>
            </div>
            <section className={PAGE_CARD_CLASS}><Skeleton height={16} width="30%" /><div className="mt-3"><SkeletonRows rows={6} /></div></section>
        </> : !hasData ? <div className={UNAVAILABLE_STATE_CLASS} role="status">Belum ada volume kendaraan teragregasi pada filter ini.</div> : <>
            <AnalyticsMeasureBand items={[
                { label: "Resolusi", value: data?.bucket ?? "–" },
                { label: "Sampel", value: data?.sample_count ?? 0 },
                { label: "Sampel estimasi", value: data?.estimated_sample_count ?? 0, tone: data?.estimated_sample_count ? "estimated" : "default" },
                { label: "Segmen terurut", value: data?.ranking.length ?? 0 },
                { label: "Titik seri", value: data?.series.length ?? 0 },
            ]} />
            <AnalyticsMetricLedger label="Ringkasan volume kendaraan" items={flowMetrics} />
            <div className="mb-3.5 flex flex-wrap items-center gap-x-3 border-y border-(--border) bg-(--surface-sunken) px-3 py-1.5">
                <span className="text-[9px] font-bold tracking-widest text-(--muted) uppercase">Seri ditampilkan</span>
                <SeriesToggles items={VEHICLES} active={activeVehicles} onToggle={(key) => toggle(key as VehicleKey)} label="Jenis kendaraan yang ditampilkan" compact />
            </div>
            <div className={ANALYTICS_CHART_GRID_CLASS}>
                <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-label="Komposisi kendaraan" aria-busy={loading}>
                    <SectionTitle title="Komposisi kendaraan" meta="Jenis aktif dibandingkan pada satu total arus." aside="kend/jam" />
                    {visible.length ? <div className={`${CHART_CLASS} ${CHART_SMALL_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 560, height: 250 }}>
                        <BarChart data={[{ name: "Total", ...Object.fromEntries(VEHICLES.map((vehicle) => [vehicle.rateKey, num(data?.totals[vehicle.key])])) }]}
                            layout="vertical" margin={{ top: 8, right: 20, bottom: 8, left: 8 }} accessibilityLayer>
                            <CartesianGrid strokeDasharray="2 5" stroke={CHART_GRID_STROKE} vertical={false} /><XAxis type="number" {...CHART_AXIS} tickFormatter={(value) => fmtIntId(Number(value))} /><YAxis type="category" dataKey="name" hide />
                            <Tooltip cursor={{ fill: "var(--selection-soft)" }} contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={vehicleTooltip} />
                            {visible.map((vehicle, index) => <Bar key={vehicle.key} dataKey={vehicle.rateKey} name={vehicle.label} stackId="composition" fill={vehicle.color} activeBar={{ stroke: "#f8fafc", strokeWidth: 1.5 }} {...entranceProps(entrance.active, index)} />)}
                        </BarChart>
                    </ResponsiveContainer></div> : <div className={UNAVAILABLE_STATE_CLASS}>Aktifkan sedikitnya satu jenis kendaraan.</div>}
                </section>
                <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS} [animation-delay:0.06s]`} aria-label="Pangsa kendaraan" aria-busy={loading}>
                    <SectionTitle title="Pangsa kendaraan" meta="Proporsi tiap jenis terhadap total volume." aside="%" />
                    {compositionData.length ? <div className={`${CHART_CLASS} ${CHART_SMALL_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 480, height: 250 }}>
                        <PieChart accessibilityLayer><Pie data={compositionData} dataKey="value" nameKey="name" innerRadius="52%" outerRadius="80%" paddingAngle={1} activeShape={renderActiveSector} {...entranceProps(entrance.active)}>
                            {compositionData.map((slice) => <Cell key={slice.name} fill={slice.fill} />)}
                        </Pie><Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={(value, name) => {
                            const slice = compositionData.find((item) => item.name === name);
                            return [`${fmtIntId(Number(value))} kend/jam${slice?.share == null ? "" : ` · ${fmtFloatId(slice.share * 100, 1)}%`}`, name];
                        }} /></PieChart>
                    </ResponsiveContainer></div> : <div className={UNAVAILABLE_STATE_CLASS}>Tidak ada jenis kendaraan yang ditampilkan.</div>}
                </section>
            </div>
            <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-label="Peringkat segmen" aria-busy={loading}>
                <SectionTitle title="Peringkat segmen" meta="Klik Saring untuk memfokuskan analitik pada satu segmen." aside={`${data?.ranking.length ?? 0} segmen`} />
                <div className={TABLE_WRAP_CLASS}><table className={PRIORITY_TABLE_CLASS}><thead><tr>
                    <th className="w-11.5 text-right text-(--secondary) tabular-nums">#</th><th>Segmen</th>
                    {VEHICLES.map((vehicle) => <th key={vehicle.key} className="text-right tabular-nums">{vehicle.label}</th>)}
                    <th className="text-right tabular-nums">Total</th>
                </tr></thead><tbody>{(data?.ranking ?? []).map((row) => <tr key={row.segment_id}>
                    <td className="w-11.5 text-right text-(--secondary) tabular-nums">{row.rank}</td>
                    <td><strong>{row.segment_name}</strong><br /><small>{row.corridor_name}</small><br />
                        <button type="button" className={`mt-1 cursor-pointer rounded-full border px-2 py-0.75 text-[10px] font-bold transition-colors duration-160 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--green) ${filter.segmentId === row.segment_id ? "border-(--green) bg-(--green) text-[#062018]" : "border-(--border) bg-transparent text-(--green) hover:border-(--green) hover:text-[#86efac]"}`}
                            aria-pressed={filter.segmentId === row.segment_id} onClick={() => filterSegment(row.segment_id)}>Saring</button></td>
                    {VEHICLES.map((vehicle) => <td key={vehicle.key} className="text-right tabular-nums">{fmtIntId(row[vehicle.rateKey])}</td>)}
                    <td className="text-right tabular-nums"><div className="relative min-w-26 overflow-hidden rounded-(--radius-badge) bg-(--surface-sunken) px-2 py-1"><span className="absolute inset-y-0 left-0 bg-(--selection) opacity-[0.18]" style={{ width: `${maxRankingTotal > 0 ? ((row.total_veh_h ?? 0) / maxRankingTotal) * 100 : 0}%` }} aria-hidden="true" /><strong className="relative">{fmtIntId(row.total_veh_h)}</strong></div></td>
                </tr>)}</tbody></table></div>
            </section>
            <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-label="Tren volume kendaraan" aria-busy={loading}>
                <SectionTitle title="Tren volume kendaraan" meta="Rata-rata per segmen, dijumlahkan antarsegmen." aside={data?.bucket ? `Per ${data.bucket}` : undefined} />
                {data?.series.length && visible.length ? <div className={`${CHART_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 800, height: 320 }}>
                    <LineChart data={data.series} margin={{ top: 20, right: 20, bottom: 12, left: 8 }} accessibilityLayer>
                        <CartesianGrid strokeDasharray="2 5" stroke={CHART_GRID_STROKE} vertical={false} /><XAxis dataKey="timestamp" tickFormatter={(value: string) => fmtChartTickId(value, query.from, query.to)} minTickGap={45} {...CHART_AXIS} /><YAxis width={68} {...CHART_AXIS} tickFormatter={(value) => fmtIntId(Number(value))} />
                        <Tooltip cursor={CHART_TOOLTIP_CURSOR} contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={vehicleTooltip} labelFormatter={(value) => fmtDateTimeId(String(value))} />
                        {visible.map((vehicle, index) => <Line key={vehicle.key} dataKey={vehicle.rateKey} name={vehicle.label} stroke={vehicle.color} strokeWidth={2} dot={false} {...entranceProps(entrance.active, index)} />)}
                    </LineChart>
                </ResponsiveContainer></div> : <div className={UNAVAILABLE_STATE_CLASS}>{visible.length ? "Belum ada tren pada periode ini." : "Aktifkan sedikitnya satu jenis kendaraan."}</div>}
            </section>
            <SectionTitle title="Vehicle kilometres travelled" meta="Jarak tempuh kendaraan per jam pada cakupan terpilih." aside="VKT" />
            <AnalyticsMetricLedger label="Vehicle kilometres travelled" items={vktMetrics} />
            <p className={ANALYTICS_NOTE_CLASS}>Total VKT: {fmtFloatId(data?.total_vkt_km_h, 1)} km/jam{data?.estimated_sample_count ? ` · ${data.estimated_sample_count} sampel estimasi occupancy` : ""}.</p>
        </>}
    </div>;
}
