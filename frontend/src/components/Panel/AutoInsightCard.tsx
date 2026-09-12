"use client";

import { MessageCircle } from "lucide-react";
import { askBangJo } from "@/utils/selectionStore";
import { useAutoInsight } from "@/hooks/useAutoInsight";
import type { AutoInsightEntity } from "@/utils/autoInsight";
import Skeleton from "@/components/ui/Skeleton";
import SectionTitle from "@/components/ui/SectionTitle";
import MarkdownText from "@/components/ui/MarkdownText";

export default function AutoInsightCard({ entity, label }: { entity: AutoInsightEntity; label: string }) {
    const { reply, loading } = useAutoInsight(entity);
    const answer = reply?.answer;
    const question = `Berikan analisis dan rekomendasi intervensi untuk ${label}.`;

    return (
        <section className="panel-section auto-insight-section">
            <SectionTitle title="Insight Bang Jo" meta={reply?.cached ? "cache" : "AI"} />
            {loading && !answer && (
                <div aria-hidden="true">
                    <Skeleton height={12} width="82%" />
                    <Skeleton height={12} width="64%" />
                </div>
            )}
            {!loading && !answer && (
                <p className="data-empty">{reply?.detail ?? "Insight belum tersedia untuk entitas ini."}</p>
            )}
            {answer && (
                <div className="auto-insight-body">
                    <MarkdownText className="auto-insight-summary">{answer.summary}</MarkdownText>
                    {answer.recommendation && (
                        <MarkdownText className="auto-insight-reco">{answer.recommendation}</MarkdownText>
                    )}
                    {answer.asi_category && <span className="auto-insight-asi">ASI: {answer.asi_category}</span>}
                </div>
            )}
            <button type="button" className="analytics-button bangjo-promote" onClick={() => askBangJo(question)}>
                <MessageCircle aria-hidden="true" /> Tanya Bang Jo
            </button>
        </section>
    );
}
