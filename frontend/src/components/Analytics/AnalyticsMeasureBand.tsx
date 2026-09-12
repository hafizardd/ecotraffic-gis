import type { ReactNode } from "react";

export interface AnalyticsMeasureItem {
    label: string;
    value: ReactNode;
    tone?: "default" | "live" | "estimated" | "stale";
}

const TONE_CLASS: Record<NonNullable<AnalyticsMeasureItem["tone"]>, string> = {
    default: "bg-[var(--contour-strong)]",
    live: "bg-[var(--brand-strong)]",
    estimated: "bg-[var(--accent)]",
    stale: "bg-[var(--danger)]",
};

export default function AnalyticsMeasureBand({
    items,
    label = "Jejak pengamatan",
}: {
    items: AnalyticsMeasureItem[];
    label?: string;
}) {
    return (
        <section
            aria-label={label}
            className="mb-[14px] overflow-hidden rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-sunken)]"
        >
            <div className="flex min-h-8 items-center gap-2 border-b border-[var(--border)] px-3 text-[9px] font-bold tracking-[0.14em] text-[var(--brand-strong)] uppercase">
                <span className="h-px w-5 bg-[var(--brand)]" aria-hidden="true" />
                {label}
            </div>
            <dl className="grid grid-cols-[repeat(auto-fit,minmax(118px,1fr))]">
                {items.map((item, index) => (
                    <div
                        key={`${item.label}-${index}`}
                        className="relative min-w-0 border-r border-[var(--border)] px-3 pt-[11px] pb-3 last:border-r-0"
                    >
                        <span
                            className={`absolute top-0 left-3 h-[3px] w-7 ${TONE_CLASS[item.tone ?? "default"]}`}
                            aria-hidden="true"
                        />
                        <dt className="text-[9px] font-bold tracking-[0.09em] text-[var(--muted)] uppercase">
                            {item.label}
                        </dt>
                        <dd className="mt-1 mb-0 overflow-hidden text-ellipsis text-[11px] leading-[1.35] font-semibold text-[var(--text)] tabular-nums">
                            {item.value}
                        </dd>
                    </div>
                ))}
            </dl>
        </section>
    );
}
