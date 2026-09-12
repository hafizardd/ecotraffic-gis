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
            {!isUser && message.contextLabel && (
                <small className="bangjo-msg-context">Konteks: {message.contextLabel}</small>
            )}
        </>
    );
}
