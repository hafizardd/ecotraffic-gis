"use client";

interface SkeletonProps {
    width?: number | string;
    height?: number | string;
    radius?: number | string;
    className?: string;
}

export default function Skeleton({ width = "100%", height = 16, radius, className }: SkeletonProps) {
    return <span className={`skeleton${className ? ` ${className}` : ""}`} style={{ width, height, borderRadius: radius }} aria-hidden="true" />;
}

const CHART_BAR_HEIGHTS = ["38%", "62%", "46%", "78%", "54%", "88%", "42%", "70%", "58%"];

export function ChartSkeleton({ bars = 9, height = 220 }: { bars?: number; height?: number | string }) {
    return (
        <div className="skeleton-chart" style={{ height }} aria-hidden="true">
            {Array.from({ length: bars }, (_, index) => (
                <Skeleton key={index} height={CHART_BAR_HEIGHTS[index % CHART_BAR_HEIGHTS.length]} radius={4} />
            ))}
        </div>
    );
}

export function SkeletonRows({ rows = 5, height = 46 }: { rows?: number; height?: number | string }) {
    return (
        <div className="skeleton-stack" aria-hidden="true">
            {Array.from({ length: rows }, (_, index) => <Skeleton key={index} height={height} radius={8} />)}
        </div>
    );
}
