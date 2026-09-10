"use client";

import { BangJoMessage } from "@/types";

export default function BangJoMessageBubble({ message }: { message: BangJoMessage }) {
    const isUser = message.role === "user";
    return (
        <>
            <div className={`bangjo-msg ${isUser ? "bangjo-msg-user" : "bangjo-msg-bot"}`}>{message.content}</div>
            {!isUser && message.contextLabel && (
                <small className="bangjo-msg-context">Konteks: {message.contextLabel}</small>
            )}
        </>
    );
}
