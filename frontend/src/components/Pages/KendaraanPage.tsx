"use client";
import { useCallback, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Sector, Tooltip, XAxis, YAxis } from "recharts";
import type { PieSectorDataItem } from "recharts";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fetchVehicleAnalytics } from "@/services/api";
import { fmtDateTimeId, fmtFloatId, fmtIntId } from "@/utils/format";
import AnalyticsFilters from "../Analytics/AnalyticsFilters";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton, { ChartSkeleton, SkeletonRows } from "@/components/ui/Skeleton";
import { CHART_AXIS, CHART_GRID_STROKE, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE, entranceProps, useChartEntrance } from "@/components/charts/theme";
import type { VehicleKey } from "@/types";
import { ANALYTICS_CHART_GRID_CLASS, ANALYTICS_ERROR_CLASS, ANALYTICS_NOTE_CLASS, ANIMATE_IN_CLASS, CHART_CLASS, CHART_INTERACTIVE_CLASS, CHART_SMALL_CLASS, PAGE_CARD_CLASS, PAGE_CARD_GRID_CLASS, PAGE_CONTAINER_CLASS, PRIORITY_TABLE_CLASS, SUMMARY_METRIC_CLASS, TABLE_WRAP_CLASS, UNAVAILABLE_STATE_CLASS } from "@/styles/tailwind";

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
    const { query, setFilter } = useEmissionAnalytics();
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
    function toggleFromLegend(value: unknown) { const found = VEHICLES.find((vehicle) => vehicle.label === value); if (found) toggle(found.key); }
    function legendToggle(value: unknown) { toggleFromLegend(value); }
    function filterSegment(segmentId: string) { setFilter({ segmentId, corridorId: null }); }

    return <div className={`${PAGE_CONTAINER_CLASS} [&_:focus-visible]:outline-2 [&_:focus-visible]:outline-offset-3 [&_:focus-visible]:outline-[#22c55e]`}>
        <SectionTitle page eyebrow="Analisis lalu lintas" title="Kendaraan" meta="Komposisi, peringkat segmen, VKT, dan tren volume kendaraan per jam." />
        <AnalyticsFilters />
        {error && !data ? <p role="alert" className={ANALYTICS_ERROR_CLASS}>{error}</p> : resolving ? <>
            <div className={PAGE_CARD_GRID_CLASS}>{VEHICLES.map((vehicle) => <div className={`${PAGE_CARD_CLASS} ${SUMMARY_METRIC_CLASS}`} key={vehicle.key}>
                <Skeleton height={10} width="50%" /><Skeleton height={24} width="70%" /><Skeleton height={10} width="42%" /></div>)}</div>
            <div className={ANALYTICS_CHART_GRID_CLASS}>
                <section className={PAGE_CARD_CLASS}><Skeleton height={16} width="34%" /><div className="mt-3"><ChartSkeleton bars={6} height={220} /></div></section>
                <section className={PAGE_CARD_CLASS}><Skeleton height={16} width="45%" /><div className="mt-3"><ChartSkeleton bars={6} height={220} /></div></section>
            </div>
            <section className={PAGE_CARD_CLASS}><Skeleton height={16} width="30%" /><div className="mt-3"><SkeletonRows rows={6} /></div></section>
        </> : !hasData ? <div className={UNAVAILABLE_STATE_CLASS} role="status">Belum ada volume kendaraan teragregasi pada filter ini.</div> : <>
            <div className={PAGE_CARD_GRID_CLASS}>
                {VEHICLES.map((vehicle) => <div className={`${PAGE_CARD_CLASS} ${SUMMARY_METRIC_CLASS}`} key={vehicle.key}>
                    <span style={{ color: vehicle.color }}>{vehicle.label}</span>
                    <strong>{fmtIntId(data?.totals[vehicle.key])}</strong>
                    <small>kendaraan/jam</small>
                </div>)}
            </div>
            <div className={ANALYTICS_CHART_GRID_CLASS}>
                <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-label="Komposisi kendaraan" aria-busy={loading}>
                    <SectionTitle title="Komposisi kendaraan" meta="Klik legenda untuk menyembunyikan jenis kendaraan." aside="kend/jam" />
                    <div className={`${CHART_CLASS} ${CHART_SMALL_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%">
                        <BarChart data={[{ name: "Total", ...Object.fromEntries(VEHICLES.map((vehicle) => [vehicle.rateKey, num(data?.totals[vehicle.key])])) }]}
                            layout="vertical" margin={{ top: 8, right: 20, bottom: 8, left: 8 }} accessibilityLayer>
                            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} /><XAxis type="number" {...CHART_AXIS} tickFormatter={(value) => fmtIntId(Number(value))} /><YAxis type="category" dataKey="name" hide />
                            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={vehicleTooltip} />
                            <Legend onClick={(entry) => legendToggle((entry as { value?: string }).value)} />
                            {visible.map((vehicle, index) => <Bar key={vehicle.key} dataKey={vehicle.rateKey} name={vehicle.label} stackId="composition" fill={vehicle.color} activeBar={{ stroke: "#f8fafc", strokeWidth: 1.5 }} {...entranceProps(entrance.active, index)} />)}
                        </BarChart>
                    </ResponsiveContainer></div>
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
                    <th className="w-[46px] text-right text-[var(--secondary)] tabular-nums">#</th><th>Segmen</th>
                    {VEHICLES.map((vehicle) => <th key={vehicle.key} className="text-right tabular-nums">{vehicle.label}</th>)}
                    <th className="text-right tabular-nums">Total</th>
                </tr></thead><tbody>{(data?.ranking ?? []).map((row) => <tr key={row.segment_id}>
                    <td className="w-[46px] text-right text-[var(--secondary)] tabular-nums">{row.rank}</td>
                    <td><strong>{row.segment_name}</strong><br /><small>{row.corridor_name}</small><br />
                        <button type="button" className="mt-1 cursor-pointer rounded-full border border-[var(--border)] bg-transparent px-2 py-[3px] text-[10px] font-bold text-[var(--green)] transition-colors duration-160 hover:border-[var(--green)] hover:text-[#86efac] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--green)]" onClick={() => filterSegment(row.segment_id)}>Saring</button></td>
                    {VEHICLES.map((vehicle) => <td key={vehicle.key} className="text-right tabular-nums">{fmtIntId(row[vehicle.rateKey])}</td>)}
                    <td className="text-right tabular-nums"><strong>{fmtIntId(row.total_veh_h)}</strong></td>
                </tr>)}</tbody></table></div>
            </section>
            <section className={`${PAGE_CARD_CLASS} ${ANIMATE_IN_CLASS}`} aria-label="Tren volume kendaraan" aria-busy={loading}>
                <SectionTitle title="Tren volume kendaraan" meta="Rata-rata per segmen, dijumlahkan antarsegmen." aside={data?.bucket ? `Per ${data.bucket}` : undefined} />
                {data?.series.length ? <div className={`${CHART_CLASS} ${CHART_INTERACTIVE_CLASS}`}><ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.series} margin={{ top: 20, right: 20, bottom: 12, left: 8 }} accessibilityLayer>
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} /><XAxis dataKey="timestamp" tickFormatter={(value: string) => new Date(value).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })} minTickGap={45} {...CHART_AXIS} /><YAxis width={76} {...CHART_AXIS} tickFormatter={(value) => fmtIntId(Number(value))} />
                        <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={vehicleTooltip} labelFormatter={(value) => fmtDateTimeId(String(value))} />
                        <Legend onClick={(entry) => legendToggle((entry as { value?: string }).value)} />
                        {visible.map((vehicle, index) => <Line key={vehicle.key} dataKey={vehicle.rateKey} name={vehicle.label} stroke={vehicle.color} strokeWidth={2} dot={false} {...entranceProps(entrance.active, index)} />)}
                    </LineChart>
                </ResponsiveContainer></div> : <div className={UNAVAILABLE_STATE_CLASS}>Belum ada tren pada periode ini.</div>}
            </section>
            <div className={PAGE_CARD_GRID_CLASS}>
                {VEHICLES.map((vehicle) => <div className={`${PAGE_CARD_CLASS} ${SUMMARY_METRIC_CLASS}`} key={vehicle.key}>
                    <span style={{ color: vehicle.color }}>VKT {vehicle.label}</span>
                    <strong>{fmtFloatId(data?.vkt[vehicle.key], 1)}</strong>
                    <small>km/jam</small>
                </div>)}
            </div>
            <p className={ANALYTICS_NOTE_CLASS}>Total VKT: {fmtFloatId(data?.total_vkt_km_h, 1)} km/jam{data?.estimated_sample_count ? ` · ${data.estimated_sample_count} sampel estimasi occupancy` : ""}.</p>
        </>}
    </div>;
}
