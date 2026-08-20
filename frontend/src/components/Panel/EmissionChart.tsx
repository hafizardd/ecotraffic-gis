"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchCameraEmissions } from "@/services/api";
import { ChartPoint, EmissionUpdate } from "@/types";

interface EmissionChartProps { cameraId: string; liveEmission: EmissionUpdate | null; }
const formatTime = (ts: string) => ts.slice(11, 19);
const lines = [
    { key: "co", color: "#f05252", name: "CO" },
    { key: "nmvoc", color: "#4c8dff", name: "NMVOC" },
    { key: "nox", color: "#f5a524", name: "NOx" },
    { key: "pm", color: "#a87bff", name: "PM" },
] as const;

export default function EmissionChart({ cameraId, liveEmission }: EmissionChartProps) {
    const [chartData, setChartData] = useState<ChartPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        let active = true;
        const stateTimer = window.setTimeout(() => { if (active) { setLoading(true); setError(false); } }, 0);
        fetchCameraEmissions(cameraId, 50).then((res) => {
            if (!active) return;
            setChartData(res.emissions.map((row) => ({ timestamp: row.timestamp, co: row.total_co_g_per_min, nox: row.total_nox_g_per_min, pm: row.total_pm_g_per_min, nmvoc: row.total_nmvoc_g_per_min })).sort((a, b) => a.timestamp.localeCompare(b.timestamp)));
        }).catch(() => active && setError(true)).finally(() => active && setLoading(false));
        return () => { active = false; window.clearTimeout(stateTimer); };
    }, [cameraId]);

    useEffect(() => {
        if (!liveEmission) return;
        const timer = window.setTimeout(() => setChartData((prev) => {
                const point: ChartPoint = { timestamp: liveEmission.timestamp, co: liveEmission.total_co_g_per_min, nox: liveEmission.total_nox_g_per_min, pm: liveEmission.total_pm_g_per_min, nmvoc: liveEmission.total_nmvoc_g_per_min };
                return [...prev.filter((item) => item.timestamp !== point.timestamp), point].sort((a, b) => a.timestamp.localeCompare(b.timestamp)).slice(-50);
            }), 0);
        return () => window.clearTimeout(timer);
    }, [liveEmission]);

    if (loading) return <div className="chart-state"><span className="loading-spinner" />Memuat data tren...</div>;
    if (error) return <div className="chart-state error-state"><strong>Data tren tidak tersedia</strong><span>Riwayat emisi gagal dimuat.</span></div>;
    if (!chartData.length) return <div className="chart-state"><strong>Belum ada data tren emisi</strong><span>Data akan muncul setelah monitoring dimulai.</span></div>;

    return <div className="chart-wrap">
        {chartData.length === 1 && <div className="chart-note">Menunggu data berikutnya untuk membentuk tren</div>}
        <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData} margin={{ top: 12, right: 10, left: 2, bottom: 4 }}>
                <CartesianGrid stroke="#213147" strokeDasharray="3 5" vertical={false} />
                <XAxis dataKey="timestamp" tickFormatter={formatTime} minTickGap={34} tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "#27364a" }} />
                <YAxis width={44} tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: "g/min", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 10 }} />
                <Tooltip labelFormatter={(value) => formatTime(String(value))} contentStyle={{ backgroundColor: "#091625", border: "1px solid #26364b", borderRadius: "10px", boxShadow: "0 14px 35px rgba(0,0,0,.35)", fontSize: "12px" }} labelStyle={{ color: "#94a3b8", marginBottom: 6 }} formatter={(value, name) => [`${Number(value).toFixed(2)} g/min`, name]} />
                <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: "11px", color: "#94a3b8", paddingTop: 8 }} />
                {lines.map(({ key, color, name }) => <Line key={key} type="monotone" dataKey={key} name={name} stroke={color} strokeWidth={2} dot={chartData.length === 1 ? { r: 4, fill: color, strokeWidth: 0 } : { r: 2, fill: color, strokeWidth: 0 }} activeDot={{ r: 4 }} isAnimationActive={false} />)}
            </LineChart>
        </ResponsiveContainer>
    </div>;
}
