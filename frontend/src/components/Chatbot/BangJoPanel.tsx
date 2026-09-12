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
            className={`bangjo-panel fixed top-[84px] right-[var(--bangjo-offset-right,22px)] bottom-[22px] z-41 flex w-[min(396px,calc(100vw-32px))] flex-col overflow-hidden rounded-[var(--radius-md)] border border-[var(--contour-strong)] bg-[var(--surface)] shadow-[var(--shadow-float)] animate-[panel-in_0.24s_ease-out] motion-reduce:animate-none max-[760px]:inset-0 max-[760px]:z-50 max-[760px]:w-auto max-[760px]:rounded-none max-[760px]:border-0 ${minimized ? "top-auto h-auto max-[760px]:inset-x-0 max-[760px]:top-auto max-[760px]:bottom-0 max-[760px]:rounded-t-[var(--radius-md)]" : ""}`}
        >
            <div className={PANEL_HEADER_CLASS}>
                <div className={PANEL_ICON_CLASS}><Bot aria-hidden="true" /></div>
                <div className={PANEL_TITLE_CLASS}><span>Asisten EcoTraffic</span><h2>Bang Jo</h2></div>
                <div className="hidden items-center gap-1.5 pr-1 text-[9px] font-bold tracking-[0.08em] text-[var(--brand-strong)] uppercase min-[420px]:flex"><i className="h-1.5 w-1.5 rounded-full bg-[var(--green)]" /> Online</div>
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
                    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overscroll-contain px-4 py-4 [scrollbar-color:var(--contour-strong)_transparent] [scrollbar-gutter:stable] [scrollbar-width:thin]">
                        {!started && <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[rgba(9,26,34,0.46)] p-3">
                            <span className="mb-1 block text-[9px] font-bold tracking-[0.1em] text-[var(--selection)] uppercase">Konteks spasial</span>
                            <p className="m-0 text-[11px] leading-[1.65] text-[var(--secondary)]">Pilih objek di peta atau tanyakan tentang data lalu lintas, emisi, dan prioritas intervensi.</p>
                        </div>}
                        {!started && <BangJoQuickQuestions onSelect={onSend} />}
                        <div className="flex flex-col gap-3" aria-live="polite">
                            {messages.map((message) => <BangJoMessageBubble key={message.id} message={message} />)}
                            {isTyping && <div className="flex self-start gap-1 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2.5" role="status" aria-label="Bang Jo sedang menyusun jawaban"><i className="h-1 w-1 animate-[bangjo-pulse_1.1s_ease-in-out_infinite] rounded-full bg-[var(--muted)] motion-reduce:animate-none" /><i className="h-1 w-1 animate-[bangjo-pulse_1.1s_ease-in-out_infinite] rounded-full bg-[var(--muted)] [animation-delay:0.18s] motion-reduce:animate-none" /><i className="h-1 w-1 animate-[bangjo-pulse_1.1s_ease-in-out_infinite] rounded-full bg-[var(--muted)] [animation-delay:0.36s] motion-reduce:animate-none" /></div>}
                        </div>
                    </div>
                    <BangJoComposer disabled={isTyping} onSend={onSend} />
                    <p className="m-0 px-4 pt-0 pb-3 text-[9px] leading-4 text-[var(--muted)]">Jawaban mengikuti data dan konteks pilihan yang tersedia di dashboard.</p>
                </>
            )}
        </div>
    );
}
