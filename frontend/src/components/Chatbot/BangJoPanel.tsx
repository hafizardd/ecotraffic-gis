"use client";

import { useEffect, useRef } from "react";
import { Bot, Minus, X } from "lucide-react";
import { BangJoMessage } from "@/types";
import BangJoQuickQuestions from "./BangJoQuickQuestions";
import BangJoMessageBubble from "./BangJoMessage";
import BangJoComposer from "./BangJoComposer";
import { PANEL_CLOSE_CLASS, PANEL_HEADER_CLASS, PANEL_ICON_CLASS, PANEL_TITLE_CLASS } from "@/styles/tailwind";

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
            className={`bangjo-panel fixed top-[84px] right-[var(--bangjo-offset-right,22px)] bottom-[22px] z-41 flex w-[min(384px,calc(100vw-32px))] flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[#081522] shadow-[0_16px_42px_rgba(0,0,0,0.24)] animate-[panel-in_0.24s_ease-out] motion-reduce:animate-none max-[760px]:inset-0 max-[760px]:z-50 max-[760px]:w-auto max-[760px]:rounded-none max-[760px]:border-0 ${minimized ? "top-auto h-auto max-[760px]:inset-x-0 max-[760px]:top-auto max-[760px]:bottom-0 max-[760px]:rounded-t-[10px]" : ""}`}
        >
            <div className={PANEL_HEADER_CLASS}>
                <div className={PANEL_ICON_CLASS}><Bot aria-hidden="true" /></div>
                <div className={PANEL_TITLE_CLASS}><span>ASISTEN ECOTRAFFIC</span><h2>Bang Jo</h2></div>
                <div className="flex items-center gap-1.5 pr-1 text-[8px] font-extrabold tracking-[0.1em] text-[#4ade80] uppercase"><i className="h-[7px] w-[7px] rounded-full bg-[var(--green)] shadow-[0_0_0_4px_rgba(34,197,94,0.12)]" /> Online</div>
                <div className="flex gap-1.5">
                    <button
                        type="button"
                        className={PANEL_CLOSE_CLASS}
                        onClick={onMinimize}
                        aria-label={minimized ? "Pulihkan panel Bang Jo" : "Perkecil panel Bang Jo"}
                        aria-expanded={!minimized}
                    >
                        <Minus aria-hidden="true" />
                    </button>
                    <button type="button" className={PANEL_CLOSE_CLASS} onClick={onClose} aria-label="Tutup asisten Bang Jo">
                        <X aria-hidden="true" />
                    </button>
                </div>
            </div>

            {!minimized && (
                <>
                    <div className="flex min-h-0 flex-1 flex-col gap-[11px] overflow-y-auto px-[15px] py-[13px] [scrollbar-color:#26364a_transparent] [scrollbar-width:thin]">
                        {!started && <p className="m-0 text-[11px] leading-[1.55] text-[var(--secondary)]">Halo! Saya bisa membantu membaca data lalu lintas dan emisi.</p>}
                        {!started && <BangJoQuickQuestions onSelect={onSend} />}
                        <div className="flex flex-col gap-[9px]" aria-live="polite">
                            {messages.map((message) => <BangJoMessageBubble key={message.id} message={message} />)}
                            {isTyping && <div className="flex self-start gap-1 rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3 py-[9px] [&>i]:h-1 [&>i]:w-1 [&>i]:animate-[bangjo-pulse_1.1s_ease-in-out_infinite] [&>i]:rounded-full [&>i]:bg-[var(--muted)] [&>i:nth-child(2)]:[animation-delay:0.18s] [&>i:nth-child(3)]:[animation-delay:0.36s] motion-reduce:[&>i]:animate-none motion-reduce:[&>i]:opacity-60"><i /><i /><i /></div>}
                        </div>
                    </div>
                    <BangJoComposer disabled={isTyping} onSend={onSend} />
                    <p className="m-0 px-[15px] pt-0 pb-[11px] text-[8px] text-[var(--muted)]">Jawaban menggunakan data dashboard yang tersedia.</p>
                </>
            )}
        </div>
    );
}
