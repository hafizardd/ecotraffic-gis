"use client";

import { BangJoMessage } from "@/types";
import MarkdownText from "@/components/ui/MarkdownText";

export default function BangJoMessageBubble({ message }: { message: BangJoMessage }) {
    const isUser = message.role === "user";
    return (
        <>
            <div className={`bangjo-msg ${isUser ? "bangjo-msg-user" : "bangjo-msg-bot"}`}>
                {isUser ? message.content : <MarkdownText>{message.content}</MarkdownText>}
            </div>
            {!isUser && message.citations && message.citations.length > 0 && (
                <ul className="bangjo-citations">
                    {message.citations.map((citation, index) => (
                        <li key={`${citation.label}-${index}`}>
                            {citation.label}
                            {citation.source ? ` · ${citation.source}` : ""}
                        </li>
                    ))}
                </ul>
            )}
            {!isUser && message.contextLabel && (
                <small className="bangjo-msg-context">Konteks: {message.contextLabel}</small>
            )}
        </>
    );
}
