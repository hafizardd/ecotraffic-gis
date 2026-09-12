import type { ReactNode } from "react";

interface SectionTitleProps {
    title: ReactNode;
    eyebrow?: ReactNode;
    meta?: ReactNode;
    aside?: ReactNode;
    page?: boolean;
    as?: "h1" | "h2" | "h3";
    className?: string;
}

export default function SectionTitle({ title, eyebrow, meta, aside, page, as, className }: SectionTitleProps) {
    const Heading = as ?? (page ? "h1" : "h2");
    return (
        <div className={`mb-3.5 flex min-w-0 flex-col gap-1.25 ${page ? "mb-5" : ""}${className ? ` ${className}` : ""}`}>
            <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 flex-col gap-1.25">
                    {eyebrow && <span className="text-[10px] font-bold tracking-[0.14em] text-(--brand-strong) uppercase">{eyebrow}</span>}
                    <Heading className={`m-0 font-(family-name:--font-display) font-semibold leading-tight tracking-[-0.02em] text-(--text) ${page ? "text-(--text-section)! leading-[1.2]!" : "text-(--text-card-title)"}`}>{title}</Heading>
                </div>
                {aside && <span className="flex-[0_0_auto] text-right text-(--text-meta) font-semibold text-(--secondary) tabular-nums [&>div]:min-w-37.5 [&>div]:w-auto">{aside}</span>}
            </div>
            {meta && <p className="m-0 max-w-[72ch] text-(--text-meta) leading-[1.55] text-(--secondary)">{meta}</p>}
        </div>
    );
}
