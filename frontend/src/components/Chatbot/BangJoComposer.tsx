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
        <form className="flex items-center gap-2 border-t border-[var(--border)] px-[15px] pt-[11px] pb-[9px]" onSubmit={(event) => { event.preventDefault(); submit(); }}>
            <input
                className="min-h-[38px] min-w-0 flex-1 rounded-md border border-[#334155] bg-[#102238] px-[11px] py-2 text-[11px] text-[#edf5ff] placeholder:text-[var(--muted)]"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder="Tanyakan tentang emisi atau lalu lintas..."
                aria-label="Pesan untuk Bang Jo"
                autoFocus
            />
            <button
                type="submit"
                className={`grid h-[34px] w-[34px] flex-[0_0_34px] cursor-pointer place-items-center rounded-full border border-[#355269] bg-[#142e3b] text-[var(--muted)] transition-[background,border-color,color] duration-180 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--green)] disabled:cursor-default disabled:opacity-50 [&>svg]:w-[15px] ${canSend ? "border-[var(--green)] bg-[var(--green)] text-[#06111f]" : ""}`}
                disabled={!canSend}
                aria-label="Kirim pesan"
            >
                <Send aria-hidden="true" />
            </button>
        </form>
    );
}
