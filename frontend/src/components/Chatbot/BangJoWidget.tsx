"use client";

import { useState } from "react";
import useBangJoChat from "@/hooks/useBangJoChat";
import BangJoFab from "./BangJoFab";
import BangJoPanel from "./BangJoPanel";

export default function BangJoWidget() {
    const [open, setOpen] = useState(false);
    const [minimized, setMinimized] = useState(false);
    const { messages, isTyping, sendMessage } = useBangJoChat();

    return (
        <>
            {!open && <BangJoFab onOpen={() => { setOpen(true); setMinimized(false); }} />}
            {open && (
                <BangJoPanel
                    messages={messages}
                    isTyping={isTyping}
                    minimized={minimized}
                    onSend={sendMessage}
                    onMinimize={() => setMinimized((value) => !value)}
                    onClose={() => { setOpen(false); setMinimized(false); }}
                />
            )}
        </>
    );
}
