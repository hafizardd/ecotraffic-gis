"use client";

interface SkeletonProps {
    width?: number | string;
    height?: number | string;
    radius?: number | string;
    className?: string;
}

export default function Skeleton({ width = "100%", height = 16, radius, className }: SkeletonProps) {
    return <span className={`relative block overflow-hidden rounded-[var(--radius-sm)] bg-[#13263b] after:absolute after:inset-0 after:-translate-x-full after:bg-[linear-gradient(90deg,transparent,rgba(148,163,184,0.16),transparent)] after:animate-[skeleton-shimmer_1.4s_ease-in-out_infinite] after:content-[''] motion-reduce:after:animate-none${className ? ` ${className}` : ""}`} style={{ width, height, borderRadius: radius }} aria-hidden="true" />;
}

const CHART_BAR_HEIGHTS = ["38%", "62%", "46%", "78%", "54%", "88%", "42%", "70%", "58%"];

export function ChartSkeleton({ bars = 9, height = 220 }: { bars?: number; height?: number | string }) {
    return (
        <div className="flex h-full items-end gap-2 [&>span]:flex-1" style={{ height }} aria-hidden="true">
            {Array.from({ length: bars }, (_, index) => (
                <Skeleton key={index} height={CHART_BAR_HEIGHTS[index % CHART_BAR_HEIGHTS.length]} radius={4} />
            ))}
        </div>
    );
}

export function SkeletonRows({ rows = 5, height = 46 }: { rows?: number; height?: number | string }) {
    return (
        <div className="grid gap-2" aria-hidden="true">
            {Array.from({ length: rows }, (_, index) => <Skeleton key={index} height={height} radius={8} />)}
        </div>
    );
}
