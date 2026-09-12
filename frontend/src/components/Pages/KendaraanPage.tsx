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
    function toggleFromLegend(value: unknown) { const found = VEHICLES.find((vehicle) => vehicle.label === value); if (found) toggle(found.key); }
    function legendToggle(value: unknown) { toggleFromLegend(value); }
    function filterSegment(segmentId: string) {
        // Toggle: clicking the focused segment again clears the focus.
        setFilter(filter.segmentId === segmentId ? { segmentId: null } : { segmentId, corridorId: null });
    }

    return <div className="page-container analytics-page">
        <SectionTitle page eyebrow="Analisis lalu lintas" title="Kendaraan" meta="Komposisi, peringkat segmen, VKT, dan tren volume kendaraan per jam." />
        <AnalyticsFilters />
        {error && !data ? <p role="alert" className="analytics-error">{error}</p> : resolving ? <>
            <div className="page-card-grid">{VEHICLES.map((vehicle) => <div className="page-card summary-metric" key={vehicle.key}>
                <Skeleton height={10} width="50%" /><Skeleton height={24} width="70%" /><Skeleton height={10} width="42%" /></div>)}</div>
            <div className="analytics-chart-grid">
                <section className="page-card"><Skeleton height={16} width="34%" /><div style={{ marginTop: 12 }}><ChartSkeleton bars={6} height={220} /></div></section>
                <section className="page-card"><Skeleton height={16} width="45%" /><div style={{ marginTop: 12 }}><ChartSkeleton bars={6} height={220} /></div></section>
            </div>
            <section className="page-card"><Skeleton height={16} width="30%" /><div style={{ marginTop: 12 }}><SkeletonRows rows={6} /></div></section>
        </> : !hasData ? <div className="unavailable-state" role="status">Belum ada volume kendaraan teragregasi pada filter ini.</div> : <>
            <div className="page-card-grid">
                {VEHICLES.map((vehicle) => <div className="page-card summary-metric" key={vehicle.key}>
                    <span style={{ color: vehicle.color }}>{vehicle.label}</span>
                    <strong>{fmtIntId(data?.totals[vehicle.key])}</strong>
                    <small>kendaraan/jam</small>
                </div>)}
            </div>
            <div className="analytics-chart-grid">
                <section className="page-card animate-in" aria-label="Komposisi kendaraan" aria-busy={loading}>
                    <SectionTitle title="Komposisi kendaraan" meta="Klik legenda untuk menyembunyikan jenis kendaraan." aside="kend/jam" />
                    <div className="analytics-chart analytics-chart-small chart-interactive"><ResponsiveContainer width="100%" height="100%">
                        <BarChart data={[{ name: "Total", ...Object.fromEntries(VEHICLES.map((vehicle) => [vehicle.rateKey, num(data?.totals[vehicle.key])])) }]}
                            layout="vertical" margin={{ top: 8, right: 20, bottom: 8, left: 8 }} accessibilityLayer>
                            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} /><XAxis type="number" {...CHART_AXIS} tickFormatter={(value) => fmtIntId(Number(value))} /><YAxis type="category" dataKey="name" hide />
                            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={vehicleTooltip} />
                            <Legend onClick={(entry) => legendToggle((entry as { value?: string }).value)} />
                            {visible.map((vehicle, index) => <Bar key={vehicle.key} dataKey={vehicle.rateKey} name={vehicle.label} stackId="composition" fill={vehicle.color} activeBar={{ stroke: "#f8fafc", strokeWidth: 1.5 }} {...entranceProps(entrance.active, index)} />)}
                        </BarChart>
                    </ResponsiveContainer></div>
                </section>
                <section className="page-card animate-in animate-in-delay-1" aria-label="Pangsa kendaraan" aria-busy={loading}>
                    <SectionTitle title="Pangsa kendaraan" meta="Proporsi tiap jenis terhadap total volume." aside="%" />
                    {compositionData.length ? <div className="analytics-chart analytics-chart-small chart-interactive"><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 480, height: 250 }}>
                        <PieChart accessibilityLayer><Pie data={compositionData} dataKey="value" nameKey="name" innerRadius="52%" outerRadius="80%" paddingAngle={1} activeShape={renderActiveSector} {...entranceProps(entrance.active)}>
                            {compositionData.map((slice) => <Cell key={slice.name} fill={slice.fill} />)}
                        </Pie><Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={(value, name) => {
                            const slice = compositionData.find((item) => item.name === name);
                            return [`${fmtIntId(Number(value))} kend/jam${slice?.share == null ? "" : ` · ${fmtFloatId(slice.share * 100, 1)}%`}`, name];
                        }} /></PieChart>
                    </ResponsiveContainer></div> : <div className="unavailable-state">Tidak ada jenis kendaraan yang ditampilkan.</div>}
                </section>
            </div>
            <section className="page-card animate-in" aria-label="Peringkat segmen" aria-busy={loading}>
                <SectionTitle title="Peringkat segmen" meta="Klik Saring untuk memfokuskan analitik pada satu segmen." aside={`${data?.ranking.length ?? 0} segmen`} />
                <div className="table-wrap"><table className="priority-table"><thead><tr>
                    <th className="history-index">#</th><th>Segmen</th>
                    {VEHICLES.map((vehicle) => <th key={vehicle.key} className="history-num">{vehicle.label}</th>)}
                    <th className="history-num">Total</th>
                </tr></thead><tbody>{(data?.ranking ?? []).map((row) => <tr key={row.segment_id}>
                    <td className="history-index">{row.rank}</td>
                    <td><strong>{row.segment_name}</strong><br /><small>{row.corridor_name}</small><br />
                        <button type="button" className={`link-button${filter.segmentId === row.segment_id ? " is-active" : ""}`}
                            aria-pressed={filter.segmentId === row.segment_id} onClick={() => filterSegment(row.segment_id)}>Saring</button></td>
                    {VEHICLES.map((vehicle) => <td key={vehicle.key} className="history-num">{fmtIntId(row[vehicle.rateKey])}</td>)}
                    <td className="history-num"><strong>{fmtIntId(row.total_veh_h)}</strong></td>
                </tr>)}</tbody></table></div>
            </section>
            <section className="page-card animate-in" aria-label="Tren volume kendaraan" aria-busy={loading}>
                <SectionTitle title="Tren volume kendaraan" meta="Rata-rata per segmen, dijumlahkan antarsegmen." aside={data?.bucket ? `Per ${data.bucket}` : undefined} />
                {data?.series.length ? <div className="analytics-chart chart-interactive"><ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.series} margin={{ top: 20, right: 20, bottom: 12, left: 8 }} accessibilityLayer>
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} /><XAxis dataKey="timestamp" tickFormatter={(value: string) => new Date(value).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })} minTickGap={45} {...CHART_AXIS} /><YAxis width={76} {...CHART_AXIS} tickFormatter={(value) => fmtIntId(Number(value))} />
                        <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={vehicleTooltip} labelFormatter={(value) => fmtDateTimeId(String(value))} />
                        <Legend onClick={(entry) => legendToggle((entry as { value?: string }).value)} />
                        {visible.map((vehicle, index) => <Line key={vehicle.key} dataKey={vehicle.rateKey} name={vehicle.label} stroke={vehicle.color} strokeWidth={2} dot={false} {...entranceProps(entrance.active, index)} />)}
                    </LineChart>
                </ResponsiveContainer></div> : <div className="unavailable-state">Belum ada tren pada periode ini.</div>}
            </section>
            <div className="page-card-grid">
                {VEHICLES.map((vehicle) => <div className="page-card summary-metric" key={vehicle.key}>
                    <span style={{ color: vehicle.color }}>VKT {vehicle.label}</span>
                    <strong>{fmtFloatId(data?.vkt[vehicle.key], 1)}</strong>
                    <small>km/jam</small>
                </div>)}
            </div>
            <p className="analytics-note">Total VKT: {fmtFloatId(data?.total_vkt_km_h, 1)} km/jam{data?.estimated_sample_count ? ` · ${data.estimated_sample_count} sampel perkiraan` : ""}.</p>
        </>}
    </div>;
}
