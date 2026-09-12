"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchCameraEmissions } from "@/services/api";
import { ChartPoint, EmissionUpdate } from "@/types";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE, entranceProps, useChartEntrance } from "@/components/charts/theme";
import { formatNumber } from "@/utils/format";

interface EmissionChartProps { cameraId: string; liveEmission: EmissionUpdate | null; }
const formatTime = (ts: string) => ts.slice(11, 19);
export default function EmissionChart({ cameraId, liveEmission }: EmissionChartProps) {
    const [chartData, setChartData] = useState<ChartPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const entrance = useChartEntrance(chartData.length > 0);

    useEffect(() => {
        let active = true;
        const stateTimer = window.setTimeout(() => { if (active) { setLoading(true); setError(false); } }, 0);
        fetchCameraEmissions(cameraId, 50).then((res) => {
            if (!active) return;
            setChartData(res.emissions.map((row) => ({
                timestamp: row.timestamp,
                ...Object.fromEntries(EMISSION_DEFINITIONS.map(({ key, field }) => [key, Number(row[field] ?? 0)])),
            }) as ChartPoint).sort((a, b) => a.timestamp.localeCompare(b.timestamp)));
        }).catch(() => active && setError(true)).finally(() => active && setLoading(false));
        return () => { active = false; window.clearTimeout(stateTimer); };
    }, [cameraId]);

    useEffect(() => {
        if (!liveEmission) return;
        const timer = window.setTimeout(() => setChartData((prev) => {
                const point = {
                    timestamp: liveEmission.timestamp,
                    ...Object.fromEntries(EMISSION_DEFINITIONS.map(({ key, field }) => [key, Number(liveEmission[field] ?? 0)])),
                } as ChartPoint;
                return [...prev.filter((item) => item.timestamp !== point.timestamp), point].sort((a, b) => a.timestamp.localeCompare(b.timestamp)).slice(-50);
            }), 0);
        return () => window.clearTimeout(timer);
    }, [liveEmission]);

    if (loading) return <div className="mx-[-5px] mt-0 mb-[-4px]"><ChartSkeleton height={250} /></div>;
    if (error) return <div className="flex h-[190px] flex-col items-center justify-center gap-[7px] rounded-lg border border-dashed border-[var(--border)] text-center text-[9px] text-[var(--secondary)] [&>strong]:text-[11px] [&>strong]:text-[#f87171] [&>span]:text-[10px]"><strong>Data tren tidak tersedia</strong><span>Riwayat emisi gagal dimuat.</span></div>;
    if (!chartData.length) return <div className="flex h-[190px] flex-col items-center justify-center gap-[7px] rounded-lg border border-dashed border-[var(--border)] text-center text-[9px] text-[var(--secondary)] [&>strong]:text-[11px] [&>strong]:text-[#cbd5e1]"><strong>Belum ada data tren emisi</strong><span>Data akan muncul setelah monitoring dimulai.</span></div>;

    return <div className="mx-[-5px] mt-0 mb-[-4px] outline-none focus-visible:rounded-[var(--radius-sm)] focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-[var(--green)]">
        {chartData.length === 1 && <div className="mx-[5px] mt-0 mb-[5px] rounded-md bg-[rgba(245,165,36,0.08)] px-2 py-1.5 text-center text-[8px] text-[#e8bb5e]">Menunggu data berikutnya untuk membentuk tren</div>}
        <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData} margin={{ top: 12, right: 10, left: 2, bottom: 4 }} accessibilityLayer>
                <CartesianGrid stroke="#213147" strokeDasharray="3 5" vertical={false} />
                <XAxis dataKey="timestamp" tickFormatter={formatTime} minTickGap={34} tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "#27364a" }} />
                <YAxis width={44} tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: "g/min", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 10 }} />
                <Tooltip labelFormatter={(value) => formatTime(String(value))} contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={(value, name) => [`${formatNumber(Number(value))} g/min`, name]} />
                <Legend iconType="circle" iconSize={7} wrapperStyle={{ width: "100%", fontSize: "10px", color: "#94a3b8", paddingTop: 8, lineHeight: "20px" }} />
                {EMISSION_DEFINITIONS.map(({ key, color, label }, index) => <Line key={key} type="monotone" dataKey={key} name={label} stroke={color} strokeWidth={2} dot={chartData.length === 1 ? { r: 4, fill: color, strokeWidth: 0 } : { r: 2, fill: color, strokeWidth: 0 }} activeDot={{ r: 4 }} {...entranceProps(entrance.active, index)} />)}
            </LineChart>
        </ResponsiveContainer>
    </div>;
}
