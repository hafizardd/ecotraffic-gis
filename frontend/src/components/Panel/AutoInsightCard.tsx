"use client";

import { MessageCircle, Sparkles } from "lucide-react";
import { askBangJo } from "@/utils/selectionStore";
import { useAutoInsight } from "@/hooks/useAutoInsight";
import type { AutoInsightEntity } from "@/utils/autoInsight";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import MarkdownText from "@/components/ui/MarkdownText";

export default function AutoInsightCard({ entity, label }: { entity: AutoInsightEntity; label: string }) {
    const { reply, loading, generate, retry } = useAutoInsight(entity);
    const answer = reply?.answer;
    const question = `Berikan analisis dan rekomendasi intervensi untuk ${label}.`;
    const meta = reply ? (reply.cached ? "cache" : "AI") : "belum dibuat";
    // Idle shows the two actions side by side; once the user asks for an insight,
    // "Tanya Bang Jo" drops below the skeleton/answer and spans the panel.
    const started = loading || reply !== null;

    return (
        <section className="panel-section auto-insight-section">
            <SectionTitle title="Insight Bang Jo" meta={meta} />
            {!started && (
                <div className="auto-insight-actions">
                    <button type="button" className="analytics-button auto-insight-generate" onClick={generate}>
                        <Sparkles aria-hidden="true" /> Buat insight
                    </button>
                    <button type="button" className="analytics-button bangjo-promote" onClick={() => askBangJo(question)}>
                        <MessageCircle aria-hidden="true" /> Tanya Bang Jo
                    </button>
                </div>
            )}
            {started && (
                <>
                    {loading && !answer && (
                        <div className="auto-insight-skeleton" aria-hidden="true">
                            <Skeleton height={10} width="92%" />
                            <Skeleton height={10} width="100%" />
                            <Skeleton height={10} width="68%" />
                        </div>
                    )}
                    {!loading && !answer && (
                        <div className="auto-insight-body">
                            {reply?.detail && <p className="data-empty">{reply.detail}</p>}
                            <button type="button" className="analytics-button auto-insight-generate" onClick={retry}>
                                <Sparkles aria-hidden="true" /> Coba lagi
                            </button>
                        </div>
                    )}
                    {answer && (
                        <div className="auto-insight-body">
                            <MarkdownText className="auto-insight-summary">{answer.content}</MarkdownText>
                        </div>
                    )}
                    <button type="button" className="analytics-button bangjo-promote is-full" onClick={() => askBangJo(question)}>
                        <MessageCircle aria-hidden="true" /> Tanya Bang Jo
                    </button>
                </>
            )}
        </section>
    );
}
