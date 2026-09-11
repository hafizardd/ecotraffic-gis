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
        <div className="drawer-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
            <div className="drawer-panel" role="dialog" aria-modal="true" aria-label={title} ref={panelRef}>
                <header className="drawer-header">
                    <h2>{title}</h2>
                    <button type="button" className="drawer-close" aria-label="Tutup" onClick={onClose}><X aria-hidden="true" /></button>
                </header>
                <div className="drawer-body">{children}</div>
                {footer && <footer className="drawer-footer">{footer}</footer>}
            </div>
        </div>,
        document.body,
    );
}
