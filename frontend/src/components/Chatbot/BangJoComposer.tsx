"use client";

import { useState } from "react";
import { Send } from "lucide-react";

export default function BangJoComposer({ disabled, onSend }: { disabled: boolean; onSend: (text: string) => void }) {
    const [value, setValue] = useState("");
    const canSend = !disabled && value.trim().length > 0;

    const submit = () => {
        if (!canSend) return;
        onSend(value.trim());
        setValue("");
    };

    return (
        <form className="flex items-center gap-2 border-t border-[var(--border)] bg-[rgba(9,26,34,0.42)] px-4 pt-3 pb-2.5" onSubmit={(event) => { event.preventDefault(); submit(); }}>
            <input
                className="min-h-10 min-w-0 flex-1 rounded-[var(--radius-sm)] border border-[var(--contour-strong)] bg-[var(--surface-raised)] px-3 py-2 text-[11px] text-[var(--text)] outline-none placeholder:text-[var(--muted)] focus:border-[var(--selection)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--selection)]"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder="Tanyakan tentang emisi atau lalu lintas..."
                aria-label="Pesan untuk Bang Jo"
                autoFocus
            />
            <button
                type="submit"
                className={`grid h-10 w-10 flex-[0_0_40px] cursor-pointer place-items-center rounded-[var(--radius-sm)] border border-[var(--contour-strong)] bg-[var(--surface-raised)] text-[var(--muted)] transition-[background,border-color,color] duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--selection)] disabled:cursor-default disabled:opacity-50 [&>svg]:w-4 ${canSend ? "border-[var(--green)] bg-[var(--green)] text-[#062016]" : ""}`}
                disabled={!canSend}
                aria-label="Kirim pesan"
            >
                <Send aria-hidden="true" />
            </button>
        </form>
    );
}
