"use client";

import { MessageCircle, Sparkles } from "lucide-react";
import { askBangJo } from "@/utils/selectionStore";
import { useAutoInsight } from "@/hooks/useAutoInsight";
import type { AutoInsightEntity } from "@/utils/autoInsight";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import MarkdownText from "@/components/ui/MarkdownText";
import { ANALYTICS_BUTTON_CLASS, PANEL_SECTION_CLASS, SEGMENT_EMPTY_CLASS } from "@/styles/tailwind";

export default function AutoInsightCard({ entity, label }: { entity: AutoInsightEntity; label: string }) {
    const { reply, loading, generate, retry } = useAutoInsight(entity);
    const answer = reply?.answer;
    const question = `Berikan analisis dan rekomendasi intervensi untuk ${label}.`;
    const meta = reply ? (reply.cached ? "cache" : "AI") : "belum dibuat";
    // Idle shows the two actions side by side; once the user asks for an insight,
    // "Tanya Bang Jo" drops below the skeleton/answer and spans the panel.
    const started = loading || reply !== null;

    return (
        <section className={PANEL_SECTION_CLASS}>
            <SectionTitle title="Insight Bang Jo" eyebrow="Konteks keputusan" meta={meta} />
            {!started && (
                <div className="mb-2.5 grid grid-cols-2 gap-2">
                    <button type="button" className={`${ANALYTICS_BUTTON_CLASS} inline-flex items-center justify-center gap-2`} onClick={generate}>
                        <Sparkles aria-hidden="true" /> Buat insight
                    </button>
                    <button type="button" className={`${ANALYTICS_BUTTON_CLASS} inline-flex items-center justify-center gap-2`} onClick={() => askBangJo(question)}>
                        <MessageCircle aria-hidden="true" /> Tanya Bang Jo
                    </button>
                </div>
            )}
            {started && (
                <>
                    {loading && !answer && (
                        <div role="status" aria-label="Memuat insight Bang Jo" className="mb-2.5 grid gap-1.75">
                            <Skeleton height={10} width="92%" />
                            <Skeleton height={10} width="100%" />
                            <Skeleton height={10} width="68%" />
                        </div>
                    )}
                    {!loading && !answer && (
                        <div className="mb-3 grid gap-2">
                            {reply?.detail && <p className={SEGMENT_EMPTY_CLASS}>{reply.detail}</p>}
                            <button type="button" className={`${ANALYTICS_BUTTON_CLASS} inline-flex items-center justify-center gap-2`} onClick={retry}>
                                <Sparkles aria-hidden="true" /> Coba lagi
                            </button>
                        </div>
                    )}
                    {answer && (
                        <div className="mb-3 rounded-md border border-(--border) bg-[rgba(9,26,34,0.42)] p-3">
                            <MarkdownText className="m-0 text-[11px] leading-[1.65] text-(--text) [overflow-wrap:anywhere]">{answer.content}</MarkdownText>
                        </div>
                    )}
                    <button type="button" className={`${ANALYTICS_BUTTON_CLASS} flex w-full items-center justify-center gap-2`} onClick={() => askBangJo(question)}>
                        <MessageCircle aria-hidden="true" /> Tanya Bang Jo
                    </button>
                </>
            )}
        </section>
    );
}
