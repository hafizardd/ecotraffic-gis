"use client";

import { MessageCircle } from "lucide-react";
import { askBangJo } from "@/utils/selectionStore";
import { useAutoInsight } from "@/hooks/useAutoInsight";
import type { AutoInsightEntity } from "@/utils/autoInsight";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import MarkdownText from "@/components/ui/MarkdownText";
import { ANALYTICS_BUTTON_CLASS, PANEL_SECTION_CLASS, SEGMENT_EMPTY_CLASS } from "@/styles/tailwind";

export default function AutoInsightCard({ entity, label }: { entity: AutoInsightEntity; label: string }) {
    const { reply, loading } = useAutoInsight(entity);
    const answer = reply?.answer;
    const question = `Berikan analisis dan rekomendasi intervensi untuk ${label}.`;

    return (
        <section className={PANEL_SECTION_CLASS}>
            <SectionTitle title="Insight Bang Jo" eyebrow="Konteks keputusan" meta={reply?.context_label ?? (reply?.cached ? "Sumber: cache" : "Sumber: AI")} />
            {loading && !answer && (
                <div role="status" aria-label="Memuat insight Bang Jo">
                    <Skeleton className="mb-2" height={12} width="82%" />
                    <Skeleton height={12} width="64%" />
                </div>
            )}
            {!loading && !answer && (
                <p className={SEGMENT_EMPTY_CLASS}>{reply?.detail ?? "Insight belum tersedia untuk entitas ini."}</p>
            )}
            {answer && (
                <article className="mb-3 grid gap-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[rgba(9,26,34,0.42)] p-3">
                    <div>
                        <span className="mb-1 block text-[9px] font-bold tracking-[0.1em] text-[var(--muted)] uppercase">Ringkasan</span>
                        <MarkdownText className="m-0 text-[11px] leading-[1.65] text-[var(--text)] [overflow-wrap:anywhere]">{answer.summary}</MarkdownText>
                    </div>
                    {answer.recommendation && (
                        <div className="border-t border-[var(--border)] pt-3">
                            <span className="mb-1 block text-[9px] font-bold tracking-[0.1em] text-[var(--accent)] uppercase">Rekomendasi</span>
                            <MarkdownText className="m-0 text-[11px] leading-[1.65] text-[var(--secondary)] [overflow-wrap:anywhere]">{answer.recommendation}</MarkdownText>
                        </div>
                    )}
                    {answer.asi_category && <span className="w-max max-w-full rounded-[var(--radius-badge)] border border-[rgba(34,197,94,0.3)] bg-[var(--brand-soft)] px-2 py-1 text-[9px] font-bold tracking-[0.06em] text-[var(--brand-strong)] uppercase [overflow-wrap:anywhere]">ASI · {answer.asi_category}</span>}
                    {answer.citations && answer.citations.length > 0 && (
                        <details className="border-t border-[var(--border)] pt-2 text-[10px] text-[var(--muted)]">
                            <summary className="cursor-pointer font-semibold text-[var(--secondary)]">Sumber pendukung ({answer.citations.length})</summary>
                            <ul className="mt-2 mb-0 grid gap-1.5 pl-4 [overflow-wrap:anywhere]">
                                {answer.citations.map((citation, index) => <li key={`${citation.label}-${index}`}>{citation.label}{citation.source ? ` · ${citation.source}` : ""}</li>)}
                            </ul>
                        </details>
                    )}
                </article>
            )}
            <button type="button" className={`${ANALYTICS_BUTTON_CLASS} inline-flex w-full items-center justify-center gap-2`} onClick={() => askBangJo(question)}>
                <MessageCircle aria-hidden="true" /> Tanya Bang Jo
            </button>
        </section>
    );
}
