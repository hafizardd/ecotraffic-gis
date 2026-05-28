"use client";
import { useEffect, useState } from "react";
import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    Legend,
} from "recharts";
import { fetchCameraEmissions } from "@/services/api";
import { EmissionUpdate, ChartPoint } from "@/types";
interface EmissionChartProps {
    cameraId: string;
    liveEmission: EmissionUpdate | null;
}
const formatTime = (ts: string) => ts.slice(11, 19);
export default function EmissionChart({ cameraId, liveEmission }: EmissionChartProps) {
    const [chartData, setChartData] = useState<ChartPoint[]>([]);
    // Fetch initial 50 historical rows on mount
    useEffect(() => {
        fetchCameraEmissions(cameraId, 50).then((res) => {
            const points: ChartPoint[] = res.emissions.map((row) => ({
                timestamp: row.timestamp,
                co: row.total_co_g_per_min,
                nox: row.total_nox_g_per_min,
                pm: row.total_pm_g_per_min,
                nmvoc: row.total_nmvoc_g_per_min,
            }));
            setChartData(points);
        });
    }, [cameraId]);
    // Append live updates, keep rolling window of 50
    useEffect(() => {
        if (!liveEmission) return;
        setChartData((prev) => {
            const next: ChartPoint[] = [
                ...prev,
                {
                    timestamp: liveEmission.timestamp,
                    co: liveEmission.total_co_g_per_min,
                    nox: liveEmission.total_nox_g_per_min,
                    pm: liveEmission.total_pm_g_per_min,
                    nmvoc: liveEmission.total_nmvoc_g_per_min,
                },
            ];
            return next.slice(-50);
        });
    }, [liveEmission]);
    const lines = [
        { key: "co", color: "#ef4444", name: "CO" },
        { key: "nox", color: "#f59e0b", name: "NOx" },
        { key: "pm", color: "#8b5cf6", name: "PM" },
        { key: "nmvoc", color: "#3b82f6", name: "NMVOC" },
    ] as const;
    return (
        <div className="p-4">
            {chartData.length === 0 ? (
                <div className="text-sm text-zinc-400">Loading chart...</div>
            ) : (
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={chartData}>
                        <XAxis
                            dataKey="timestamp"
                            tickFormatter={formatTime}
                            fontSize={10}
                            tickLine={false}
                        />
                        <YAxis
                            label={{ value: "g/min", angle: -90, position: "insideLeft" }}
                            fontSize={10}
                            tickLine={false}
                            width={40}
                        />
                        <Tooltip
                            labelFormatter={(ts) => formatTime(ts)}
                            contentStyle={{
                                backgroundColor: "#18181b",
                                border: "1px solid #3f3f46",
                                borderRadius: "6px",
                            }}
                            labelStyle={{ color: "#a1a1aa" }}  // ← timestamp color
                            itemStyle={{ fontWeight: 500 }}
                        />
                        <Legend />
                        {lines.map(({ key, color, name }) => (
                            <Line
                                key={key}
                                dataKey={key}
                                name={name}
                                stroke={color}
                                dot={false}
                                strokeWidth={1.5}
                            />
                        ))}
                    </LineChart>
                </ResponsiveContainer>
            )}
        </div>
    );
}