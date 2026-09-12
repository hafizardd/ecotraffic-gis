"use client";

import { MessageCircle } from "lucide-react";
import { askBangJo } from "@/utils/selectionStore";
import { useAutoInsight } from "@/hooks/useAutoInsight";
import type { AutoInsightEntity } from "@/utils/autoInsight";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import MarkdownText from "@/components/ui/MarkdownText";
import { ANALYTICS_BUTTON_CLASS, DATA_EMPTY_CLASS, PANEL_SECTION_CLASS } from "@/styles/tailwind";

export default function AutoInsightCard({ entity, label }: { entity: AutoInsightEntity; label: string }) {
    const { reply, loading } = useAutoInsight(entity);
    const answer = reply?.answer;
    const question = `Berikan analisis dan rekomendasi intervensi untuk ${label}.`;

    return (
        <section className={PANEL_SECTION_CLASS}>
            <SectionTitle title="Insight Bang Jo" meta={reply?.cached ? "cache" : "AI"} />
            {loading && !answer && (
                <div aria-hidden="true">
                    <Skeleton className="mb-1.5" height={12} width="82%" />
                    <Skeleton height={12} width="64%" />
                </div>
            )}
            {!loading && !answer && (
                <p className={DATA_EMPTY_CLASS}>{reply?.detail ?? "Insight belum tersedia untuk entitas ini."}</p>
            )}
            {answer && (
                <div className="mb-[10px] flex flex-col gap-1.5">
                    <MarkdownText className="m-0 text-[11px] leading-[1.55] text-[var(--text)]">{answer.summary}</MarkdownText>
                    {answer.recommendation && (
                        <MarkdownText className="m-0 text-[11px] leading-[1.55] text-[var(--secondary)]">{answer.recommendation}</MarkdownText>
                    )}
                    {answer.asi_category && <span className="text-[9px] font-extrabold tracking-[0.06em] text-[var(--green)] uppercase">ASI: {answer.asi_category}</span>}
                </div>
            )}
            <button type="button" className={`${ANALYTICS_BUTTON_CLASS} inline-flex items-center gap-1.5`} onClick={() => askBangJo(question)}>
                <MessageCircle aria-hidden="true" /> Tanya Bang Jo
            </button>
        </section>
    );
}
