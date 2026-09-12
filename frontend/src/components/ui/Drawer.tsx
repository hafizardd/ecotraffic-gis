"use client";
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

const FOCUSABLE = "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";

// Right-hand slide-in panel with a dimmed backdrop. Focus is trapped while open
// and restored to the trigger on close; Escape and backdrop click both cancel.
export default function Drawer({ open, title, onClose, children, footer }: {
    open: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode;
}) {
    const panelRef = useRef<HTMLDivElement>(null);
    const restoreRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        if (!open) return;
        restoreRef.current = document.activeElement as HTMLElement | null;
        const panel = panelRef.current;
        panel?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") { event.preventDefault(); onClose(); return; }
            if (event.key !== "Tab" || !panel) return;
            const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
            if (items.length === 0) return;
            const first = items[0], last = items[items.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        };
        document.addEventListener("keydown", onKeyDown);
        return () => { document.removeEventListener("keydown", onKeyDown); restoreRef.current?.focus?.(); };
    }, [open, onClose]);

    if (!open) return null;
    return createPortal(
        <div className="fixed inset-0 z-80 flex justify-end bg-[rgba(3,13,17,0.68)] backdrop-blur-[2px]" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
            <div className="flex h-full w-[min(400px,100%)] flex-col border-l border-(--border) bg-(--surface) shadow-(--shadow-drawer) animate-[drawer-in_0.22s_ease] motion-reduce:animate-none" role="dialog" aria-modal="true" aria-label={title} ref={panelRef}>
                <header className="flex items-center justify-between border-b border-(--border) px-4.5 py-4">
                    <h2 className="m-0 font-(family-name:--font-display) text-base font-semibold">{title}</h2>
                    <button type="button" className="grid h-10 w-10 cursor-pointer place-items-center rounded-sm border border-(--border) bg-(--surface-raised) text-(--secondary) transition-colors hover:border-(--selection) hover:text-(--text) [&>svg]:h-4 [&>svg]:w-4" aria-label="Tutup" onClick={onClose}><X aria-hidden="true" /></button>
                </header>
                <div className="grid flex-1 content-start gap-5 overflow-y-auto p-4.5">{children}</div>
                {footer && <footer className="flex items-center gap-2 border-t border-(--border) px-4.5 py-3.5">{footer}</footer>}
            </div>
        </div>,
        document.body,
    );
}
