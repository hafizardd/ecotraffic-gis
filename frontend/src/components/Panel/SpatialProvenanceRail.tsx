import type { ReactNode } from "react";
import { GitCommitHorizontal } from "lucide-react";

export type ProvenanceTone = "default" | "live" | "replay" | "estimated" | "stale";

export interface ProvenanceItem {
    label: string;
    value: ReactNode;
    tone?: ProvenanceTone;
    title?: string;
}

const TONE_CLASS: Record<ProvenanceTone, string> = {
    default: "border-[var(--contour-strong)] bg-[var(--surface-raised)] text-[var(--secondary)]",
    live: "border-[rgba(34,197,94,0.42)] bg-[var(--brand-soft)] text-[var(--brand-strong)]",
    replay: "border-[rgba(56,189,248,0.42)] bg-[var(--selection-soft)] text-[#8edcff]",
    estimated: "border-[rgba(245,165,36,0.42)] bg-[rgba(245,165,36,0.1)] text-[#f5c35f]",
    stale: "border-[rgba(239,68,68,0.38)] bg-[rgba(239,68,68,0.08)] text-[#fca5a5]",
};

export function freshnessItem(value: string | null | undefined): Pick<ProvenanceItem, "value" | "tone"> | null {
    if (!value) return null;
    const normalized = value.toLowerCase();
    if (normalized === "fresh") return { value: "Segar", tone: "live" };
    if (normalized === "aging") return { value: "Menua", tone: "estimated" };
    if (normalized === "stale") return { value: "Basi", tone: "stale" };
    if (normalized === "unknown") return { value: "Belum diketahui", tone: "default" };
    return { value, tone: "default" };
}

export default function SpatialProvenanceRail({ items }: { items: Array<ProvenanceItem | null | false> }) {
    const visibleItems = items.filter(Boolean) as ProvenanceItem[];
    if (visibleItems.length === 0) return null;

    return (
        <section className="mx-4 mt-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[rgba(9,26,34,0.46)] px-3 py-3" aria-label="Provenans spasial">
            <div className="mb-2.5 flex items-center gap-2 text-[10px] font-bold tracking-[0.11em] text-[var(--muted)] uppercase">
                <GitCommitHorizontal className="h-3.5 w-3.5 text-[var(--selection)]" aria-hidden="true" />
                Provenans spasial
            </div>
            <ol className="m-0 grid list-none gap-0 p-0">
                {visibleItems.map((item, index) => {
                    const tone = item.tone ?? "default";
                    return (
                        <li className="relative grid min-w-0 grid-cols-[12px_minmax(0,1fr)] gap-2.5 pb-2.5 last:pb-0" key={`${item.label}-${index}`}>
                            {index < visibleItems.length - 1 && <span className="absolute top-2 bottom-[-2px] left-[5px] w-px bg-[var(--contour)]" aria-hidden="true" />}
                            <span className={`relative z-1 mt-[5px] h-[11px] w-[11px] rounded-full border-2 ${tone === "live" ? "border-[var(--green)] bg-[var(--green)]" : tone === "replay" ? "border-[var(--selection)] bg-[var(--selection)]" : tone === "estimated" ? "border-[var(--accent)] bg-[var(--accent)]" : tone === "stale" ? "border-[var(--danger)] bg-[var(--danger)]" : "border-[var(--contour-strong)] bg-[var(--surface)]"}`} aria-hidden="true" />
                            <div className="grid min-w-0 grid-cols-[76px_minmax(0,1fr)] items-start gap-2">
                                <span className="pt-1 text-[10px] leading-4 text-[var(--muted)]">{item.label}</span>
                                <strong className={`min-w-0 rounded-[var(--radius-badge)] border px-2 py-1 text-[10px] font-semibold leading-4 [overflow-wrap:anywhere] ${TONE_CLASS[tone]}`} title={item.title}>{item.value}</strong>
                            </div>
                        </li>
                    );
                })}
            </ol>
        </section>
    );
}
