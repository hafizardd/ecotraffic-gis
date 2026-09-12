"use client";

import { BangJoMessage } from "@/types";
import MarkdownText from "@/components/ui/MarkdownText";

export default function BangJoMessageBubble({ message }: { message: BangJoMessage }) {
    const isUser = message.role === "user";
    return (
        <article className={`flex max-w-[90%] flex-col gap-1 ${isUser ? "self-end items-end" : "self-start items-start"}`}>
            <span className={`text-[9px] font-bold tracking-[0.08em] uppercase ${isUser ? "text-[var(--muted)]" : "text-[var(--selection)]"}`}>{isUser ? "Anda" : "Bang Jo"}</span>
            <div className={`w-full rounded-[var(--radius-md)] px-3 py-2.5 text-[11px] leading-[1.65] [overflow-wrap:anywhere] ${isUser ? "whitespace-pre-wrap border border-[rgba(56,189,248,0.22)] bg-[var(--selection-soft)] text-[var(--text)]" : "whitespace-normal border border-[var(--border)] bg-[var(--surface-raised)] text-[var(--secondary)]"}`}>
                {isUser ? message.content : <MarkdownText>{message.content}</MarkdownText>}
            </div>
            {!isUser && message.citations && message.citations.length > 0 && (
                <details className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] px-2.5 py-2 text-[9px] leading-4 text-[var(--muted)]">
                    <summary className="cursor-pointer font-semibold text-[var(--secondary)]">Sumber ({message.citations.length})</summary>
                    <ul className="mt-1.5 mb-0 pl-4 [overflow-wrap:anywhere] [&>li]:list-disc">{message.citations.map((citation, index) => <li key={`${citation.label}-${index}`}>{citation.label}{citation.source ? ` · ${citation.source}` : ""}</li>)}</ul>
                </details>
            )}
            {!isUser && message.contextLabel && (
                <small className="self-start text-[9px] leading-4 text-[var(--muted)] [overflow-wrap:anywhere]">Konteks: {message.contextLabel}</small>
            )}
        </article>
    );
}
