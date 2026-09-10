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
        <form className="bangjo-composer" onSubmit={(event) => { event.preventDefault(); submit(); }}>
            <input
                className="bangjo-input"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder="Tanyakan tentang emisi atau lalu lintas..."
                aria-label="Pesan untuk Bang Jo"
                autoFocus
            />
            <button
                type="submit"
                className={`bangjo-send${canSend ? " active" : ""}`}
                disabled={!canSend}
                aria-label="Kirim pesan"
            >
                <Send aria-hidden="true" />
            </button>
        </form>
    );
}
