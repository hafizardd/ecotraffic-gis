"use client";

import { BangJoMessage } from "@/types";
import MarkdownText from "@/components/ui/MarkdownText";

export default function BangJoMessageBubble({ message }: { message: BangJoMessage }) {
    const isUser = message.role === "user";
    return (
        <>
            <div className={`max-w-[86%] rounded-[10px] px-3 py-[9px] text-[11px] leading-[1.5] [overflow-wrap:anywhere] ${isUser ? "self-end whitespace-pre-wrap bg-[var(--card-2)]" : "self-start whitespace-normal border border-[var(--border)] bg-[var(--card)]"}`}>
                {isUser ? message.content : <MarkdownText>{message.content}</MarkdownText>}
            </div>
            {!isUser && message.citations && message.citations.length > 0 && (
                <ul className="mt-[-3px] mb-0 self-start pl-4 text-[8px] leading-[1.5] text-[var(--muted)] [&>li]:list-disc">
                    {message.citations.map((citation, index) => (
                        <li key={`${citation.label}-${index}`}>
                            {citation.label}
                            {citation.source ? ` · ${citation.source}` : ""}
                        </li>
                    ))}
                </ul>
            )}
            {!isUser && message.contextLabel && (
                <small className="mt-[-5px] self-start text-[8px] text-[var(--muted)]">Konteks: {message.contextLabel}</small>
            )}
        </>
    );
}
