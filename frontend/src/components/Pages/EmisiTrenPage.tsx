"use client";
import { useCallback, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fetchEmissionTrend, fetchPollutantComposition, fetchTopEmissionCorridors } from "@/services/api";
import type { PollutantKey } from "@/types";
import { fmtDateTimeId, fmtFloatId } from "@/utils/format";
import AnalyticsFilters from "../Analytics/AnalyticsFilters";
import RealtimePollutants from "../Analytics/RealtimePollutants";
import EmissionHistory from "../Analytics/EmissionHistory";

const tooltipStyle = { backgroundColor: "#102238", border: "1px solid #334155", color: "#f8fafc" };
const numericTooltip = (value: unknown) => typeof value === "number" ? `${fmtFloatId(value, 6)} kg/hour` : "Tidak tersedia";

export default function EmisiTrenPage() {
    const { query } = useEmissionAnalytics();
    const [selected, setSelected] = useState<PollutantKey[]>(["co2", "co", "nox"]);
    const [rankPollutant, setRankPollutant] = useState<PollutantKey>("co2");
    const load = useCallback(async (signal: AbortSignal) => {
        const [trend, top, composition] = await Promise.all([
            fetchEmissionTrend(query, signal), fetchTopEmissionCorridors(query, rankPollutant, signal), fetchPollutantComposition(query, signal),
        ]);
        return { trend, top, composition };
    }, [query, rankPollutant]);
    const { data, loading, error } = useAnalyticsResource(`${JSON.stringify(query)}:${rankPollutant}`, load);
    const rankingLabel = EMISSION_DEFINITIONS.find((p) => p.key === rankPollutant)?.label;
    const composition = data?.composition.data.filter((p) => p.kg_h !== null && p.kg_h > 0) ?? [];
    function toggle(key: PollutantKey) { setSelected((values) => values.includes(key) ? values.filter((v) => v !== key) : [...values, key]); }
    const status = loading ? "Memuat analitik…" : error ?? "Tidak ada pengamatan segmen pada filter ini.";
    return <div className="page-container analytics-page">
        <div className="page-header-section"><span>ANALISIS EMISI</span><h1>Emisi & Tren</h1><p>Laju delapan polutan dari pengamatan kendaraan pada segmen jalan.</p></div>
        <AnalyticsFilters />
        <RealtimePollutants />
        <section className="page-card" aria-busy={loading} aria-label="Tren emisi">
            <div className="card-header"><strong>Tren emisi · kg/hour</strong><span>{data?.trend.bucket ? `Rata-rata per ${data.trend.bucket}` : ""}</span></div>
            <div className="analytics-pollutant-picker">{EMISSION_DEFINITIONS.map((p) => <label key={p.key} style={{ color: p.color }}><input type="checkbox" checked={selected.includes(p.key)} onChange={() => toggle(p.key)} />{p.label}</label>)}
                <button className="analytics-button" onClick={() => setSelected(EMISSION_DEFINITIONS.map((p) => p.key))}>Semua polutan</button></div>
            {loading || error || !data?.trend.data.length ? <div className="unavailable-state" role={error ? "alert" : "status"}>{status}</div> : !selected.length ? <div className="unavailable-state">Pilih polutan untuk ditampilkan.</div> :
                <div className="analytics-chart"><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 800, height: 320 }}><LineChart data={data.trend.data} margin={{ top: 20, right: 20, bottom: 12, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#24364a" /><XAxis dataKey="timestamp" tickFormatter={(v: string) => new Date(v).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })} minTickGap={45} stroke="#94a3b8" /><YAxis width={76} stroke="#94a3b8" tickFormatter={(v: number) => fmtFloatId(v, 2)} />
                    <Tooltip contentStyle={tooltipStyle} formatter={numericTooltip} labelFormatter={(v) => fmtDateTimeId(String(v))} /><Legend />
                    {EMISSION_DEFINITIONS.filter((p) => selected.includes(p.key)).map((p) => <Line key={p.key} dataKey={`${p.key}_kg_h`} name={p.label} stroke={p.color} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />)}
                </LineChart></ResponsiveContainer></div>}
            <p className="analytics-note">Rata-rata laju per segmen, lalu dijumlahkan antarsegmen untuk polutan yang sama. Cakupan segmen dapat berubah jika kamera terputus.</p>
            {data?.trend.data.some((p) => p.estimated_sample_count > 0) && <p className="analytics-note">Mencakup estimasi occupancy; metode setiap catatan tersedia di riwayat.</p>}
        </section>
        <div className="analytics-chart-grid">
            <section className="page-card" aria-label="Lima koridor dengan emisi tertinggi" aria-busy={loading}>
                <div className="card-header"><strong>Top 5 koridor · {rankingLabel}</strong><select aria-label="Polutan peringkat" value={rankPollutant} onChange={(e) => setRankPollutant(e.target.value as PollutantKey)}>{EMISSION_DEFINITIONS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}</select></div>
                {loading || error || !data?.top.data.length ? <div className="unavailable-state">{status}</div> : <>
                    <div className="analytics-chart analytics-chart-small"><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 600, height: 250 }}><BarChart data={data.top.data} layout="vertical" margin={{ top: 8, right: 20, bottom: 8, left: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#24364a" /><XAxis type="number" stroke="#94a3b8" /><YAxis type="category" dataKey="corridor_name" width={125} stroke="#94a3b8" tick={{ fontSize: 11 }} /><Tooltip contentStyle={tooltipStyle} formatter={numericTooltip} /><Bar dataKey="emission_kg_h" name={rankingLabel} fill="#22c55e" radius={[0, 4, 4, 0]} isAnimationActive={false} />
                    </BarChart></ResponsiveContainer></div>
                    <div className="table-wrap"><table className="priority-table"><thead><tr><th>#</th><th>Koridor / segmen</th><th>kg/hour</th><th>Sampel</th><th>Teramati</th></tr></thead><tbody>{data.top.data.map((row) => <tr key={row.corridor_id}><td>{row.rank}</td><td>{row.corridor_name}<br /><small>{row.segment_ids.join(", ")}{row.estimated_sample_count > 0 ? " · estimated" : ""}</small></td><td>{row.emission_kg_h == null ? "—" : fmtFloatId(row.emission_kg_h, 4)}</td><td>{row.sample_count}</td><td>{fmtDateTimeId(row.observed_at)}</td></tr>)}</tbody></table></div>
                </>}
            </section>
            <section className="page-card" aria-label="Komposisi polutan" aria-busy={loading}>
                <div className="card-header"><strong>Komposisi laju massa polutan</strong><span>kg/hour</span></div>
                {loading || error || !data?.composition.sample_count ? <div className="unavailable-state">{status}</div> : <>
                    {composition.length ? <div className="analytics-chart analytics-chart-small"><ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 480, height: 250 }}><PieChart><Pie data={composition} dataKey="kg_h" nameKey="pollutant" innerRadius="52%" outerRadius="80%" paddingAngle={1} isAnimationActive={false}>{composition.map((p) => <Cell key={p.key} fill={EMISSION_DEFINITIONS.find((d) => d.key === p.key)?.color} />)}</Pie><Tooltip contentStyle={tooltipStyle} formatter={numericTooltip} /></PieChart></ResponsiveContainer></div> : <div className="unavailable-state">Semua laju polutan teramati bernilai nol.</div>}
                    <div className="analytics-composition-legend">{data.composition.data.map((p) => <div key={p.key}><span><i style={{ background: EMISSION_DEFINITIONS.find((d) => d.key === p.key)?.color }} />{p.pollutant}</span><strong>{p.kg_h == null ? "—" : fmtFloatId(p.kg_h, 6)}</strong></div>)}</div>
                    <p className="analytics-note">Proporsi massa delapan polutan pada periode terpilih; setiap angka memiliki satuan kg/hour.</p>
                </>}
            </section>
        </div>
        <EmissionHistory />
    </div>;
}
