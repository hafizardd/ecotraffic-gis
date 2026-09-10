"use client";

import { useEffect, useRef } from "react";
import { Bot, Minus, X } from "lucide-react";
import { BangJoMessage } from "@/types";
import BangJoQuickQuestions from "./BangJoQuickQuestions";
import BangJoMessageBubble from "./BangJoMessage";
import BangJoComposer from "./BangJoComposer";

interface BangJoPanelProps {
    messages: BangJoMessage[];
    isTyping: boolean;
    minimized: boolean;
    onSend: (text: string) => void;
    onMinimize: () => void;
    onClose: () => void;
}

export default function BangJoPanel({ messages, isTyping, minimized, onSend, onMinimize, onClose }: BangJoPanelProps) {
    const panelRef = useRef<HTMLDivElement>(null);
    const started = messages.length > 0;

    useEffect(() => {
        const node = panelRef.current;
        if (!node) return;
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") { onClose(); return; }
            if (event.key !== "Tab") return;
            const focusables = Array.from(node.querySelectorAll<HTMLElement>(
                'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
            ));
            if (!focusables.length) return;
            const first = focusables[0];
            const last = focusables[focusables.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        };
        document.addEventListener("keydown", onKeyDown);
        return () => document.removeEventListener("keydown", onKeyDown);
    }, [onClose]);

    return (
        <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Bang Jo"
            className={`bangjo-panel${minimized ? " is-minimized" : ""}`}
        >
            <div className="panel-header bangjo-header">
                <div className="panel-location-icon bangjo-header-icon"><Bot aria-hidden="true" /></div>
                <div className="panel-title"><span>ASISTEN ECOTRAFFIC</span><h2>Bang Jo</h2></div>
                <div className="bangjo-status"><i /> Online</div>
                <div className="bangjo-header-actions">
                    <button
                        type="button"
                        className="panel-close"
                        onClick={onMinimize}
                        aria-label={minimized ? "Pulihkan panel Bang Jo" : "Perkecil panel Bang Jo"}
                        aria-expanded={!minimized}
                    >
                        <Minus aria-hidden="true" />
                    </button>
                    <button type="button" className="panel-close" onClick={onClose} aria-label="Tutup asisten Bang Jo">
                        <X aria-hidden="true" />
                    </button>
                </div>
            </div>

            {!minimized && (
                <>
                    <div className="panel-content bangjo-content">
                        {!started && <p className="bangjo-greeting">Halo! Saya bisa membantu membaca data lalu lintas dan emisi.</p>}
                        {!started && <BangJoQuickQuestions onSelect={onSend} />}
                        <div className="bangjo-thread" aria-live="polite">
                            {messages.map((message) => <BangJoMessageBubble key={message.id} message={message} />)}
                            {isTyping && <div className="bangjo-typing"><i /><i /><i /></div>}
                        </div>
                    </div>
                    <BangJoComposer disabled={isTyping} onSend={onSend} />
                    <p className="bangjo-disclaimer">Jawaban menggunakan data dashboard yang tersedia.</p>
                </>
            )}
        </div>
    );
}
