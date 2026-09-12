"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchCameraEmissions } from "@/services/api";
import { ChartPoint, EmissionUpdate } from "@/types";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import SeriesToggles from "@/components/Analytics/SeriesToggles";
import { CHART_AXIS, CHART_GRID_STROKE, CHART_TOOLTIP_CURSOR, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE, entranceProps, useChartEntrance } from "@/components/charts/theme";
import { fmtChartTickId, formatNumber } from "@/utils/format";
import { SEGMENT_EMPTY_CLASS } from "@/styles/tailwind";

interface EmissionChartProps { cameraId: string; liveEmission: EmissionUpdate | null; }
const formatTime = (ts: string) => ts.slice(11, 19);
export default function EmissionChart({ cameraId, liveEmission }: EmissionChartProps) {
    const [chartData, setChartData] = useState<ChartPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [selected, setSelected] = useState<Set<string>>(() => new Set(EMISSION_DEFINITIONS.map(({ key }) => key)));
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

    if (loading) return <div className="mx-[-5px] mt-0 mb-[-4px]" role="status" aria-label="Memuat tren emisi"><ChartSkeleton height={250} /></div>;
    if (error) return <div className={`${SEGMENT_EMPTY_CLASS} h-47.5 flex-col px-4 [&>strong]:text-[12px] [&>strong]:text-[#fca5a5]`} role="alert"><strong>Data tren tidak tersedia</strong><span>Riwayat emisi gagal dimuat.</span></div>;
    if (!chartData.length) return <div className={`${SEGMENT_EMPTY_CLASS} h-47.5 flex-col px-4 [&>strong]:text-[12px] [&>strong]:text-(--text)`} role="status"><strong>Belum ada data tren emisi</strong><span>Data akan muncul setelah monitoring dimulai.</span></div>;

    function toggleSeries(key: string) {
        setSelected((current) => {
            const next = new Set(current);
            if (next.has(key)) next.delete(key); else next.add(key);
            return next;
        });
    }
    const firstTimestamp = chartData.at(0)?.timestamp;
    const lastTimestamp = chartData.at(-1)?.timestamp;

    return <div className="mx-[-5px] mt-0 mb-[-4px] outline-none focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-(--green)">
        {chartData.length === 1 && <div className="mx-1.25 mt-0 mb-1.25 rounded-sm border border-[rgba(245,165,36,0.2)] bg-[rgba(245,165,36,0.08)] px-2 py-1.5 text-center text-[9px] text-[#f5c35f]">Menunggu data berikutnya untuk membentuk tren</div>}
        <SeriesToggles items={EMISSION_DEFINITIONS.map(({ key, label, color }) => ({ key, label, color }))} active={selected} onToggle={toggleSeries} label="Polutan pada grafik kamera" compact />
        {selected.size ? <ResponsiveContainer width="100%" height={250} initialDimension={{ width: 400, height: 250 }}>
            <LineChart data={chartData} margin={{ top: 12, right: 10, left: 2, bottom: 4 }} accessibilityLayer>
                <CartesianGrid stroke={CHART_GRID_STROKE} strokeDasharray="2 5" vertical={false} />
                <XAxis dataKey="timestamp" tickFormatter={(value) => fmtChartTickId(String(value), firstTimestamp, lastTimestamp)} minTickGap={34} {...CHART_AXIS} />
                <YAxis width={48} {...CHART_AXIS} axisLine={false} label={{ value: "g/min", angle: -90, position: "insideLeft", fill: "var(--muted)", fontSize: 9 }} />
                <Tooltip cursor={CHART_TOOLTIP_CURSOR} labelFormatter={(value) => formatTime(String(value))} contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={(value, name) => [`${formatNumber(Number(value))} g/min`, name]} />
                {EMISSION_DEFINITIONS.filter(({ key }) => selected.has(key)).map(({ key, color, label }, index) => <Line key={key} type="monotone" dataKey={key} name={label} stroke={color} strokeWidth={2} dot={chartData.length === 1 ? { r: 4, fill: color, strokeWidth: 0 } : false} activeDot={{ r: 4 }} connectNulls={false} {...entranceProps(entrance.active, index)} />)}
            </LineChart>
        </ResponsiveContainer> : <div className={`${SEGMENT_EMPTY_CLASS} h-40 flex-col px-4`} role="status"><strong>Grafik disembunyikan</strong><span>Aktifkan sedikitnya satu polutan.</span></div>}
    </div>;
}
