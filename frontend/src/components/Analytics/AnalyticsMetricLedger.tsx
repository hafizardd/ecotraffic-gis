import type { ReactNode } from "react";
import Skeleton from "@/components/ui/Skeleton";

export interface AnalyticsMetricItem {
    key: string;
    label: string;
    value: ReactNode;
    unit: string;
    meta?: ReactNode;
    color?: string;
    primary?: boolean;
}

export default function AnalyticsMetricLedger({
    items,
    label,
    loading = false,
}: {
    items: AnalyticsMetricItem[];
    label: string;
    loading?: boolean;
}) {
    return (
        <section
            aria-label={label}
            aria-busy={loading}
            className="mb-[14px] overflow-hidden rounded-md border border-(--border) bg-(--card)"
        >
            <dl className="grid grid-cols-[repeat(auto-fit,minmax(116px,1fr))]">
                {items.map((item) => (
                    <div
                        key={item.key}
                        className={`relative flex min-h-[94px] min-w-0 flex-col justify-center border-r border-b border-(--border) px-3 py-[13px] last:border-r-0 ${item.primary ? "bg-(--selection-soft)" : ""}`}
                    >
                        <i className="absolute top-0 left-3 h-[3px] w-7" style={{ backgroundColor: item.color ?? "var(--contour-strong)" }} aria-hidden="true" />
                        {loading ? <>
                            <Skeleton height={9} width="52%" />
                            <Skeleton height={23} width="76%" className="mt-2" />
                            <Skeleton height={8} width="44%" className="mt-2" />
                        </> : <>
                            <dt className="truncate text-[10px] font-bold tracking-[0.05em] uppercase" style={{ color: item.color ?? "var(--secondary)" }}>{item.label}</dt>
                            <dd className="mt-1 mb-0 min-w-0 font-(family-name:--font-data) text-[clamp(19px,2vw,27px)] leading-none font-semibold tracking-[-0.025em] text-(--text) tabular-nums [overflow-wrap:anywhere]">{item.value}</dd>
                            <dd className="mt-[7px] mb-0 text-[10px] leading-[1.35] text-(--muted)">{item.unit}{item.meta ? <> · {item.meta}</> : null}</dd>
                        </>}
                    </div>
                ))}
            </dl>
        </section>
    );
}
