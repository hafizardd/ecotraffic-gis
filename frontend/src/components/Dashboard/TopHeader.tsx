"use client";

import { useEffect, useState } from "react";
import { Menu } from "lucide-react";

import { useEmissionsContext } from "@/context/EmissionsContext";

export default function TopHeader({ onMenuClick, section, title }: { onMenuClick: () => void; section: string; title: string }) {
    const [now, setNow] = useState<Date | null>(null);
    const { connectionStatus, lastMessageAt } = useEmissionsContext();
    useEffect(() => {
        const initialTimer = window.setTimeout(() => setNow(new Date()), 0);
        const timer = window.setInterval(() => setNow(new Date()), 1000);
        return () => { window.clearTimeout(initialTimer); window.clearInterval(timer); };
    }, []);

    return (
        <header className="flex min-w-0 items-center gap-[18px] border-b border-[var(--border)] bg-[#081522] px-[22px] max-[760px]:gap-[10px] max-[760px]:px-3">
            <button className="hidden h-9 w-9 rounded-lg border border-[var(--border)] bg-[var(--card)] p-2 text-[var(--secondary)] max-[760px]:block [&>svg]:w-full" onClick={onMenuClick} aria-label="Buka menu">
                <Menu aria-hidden="true" />
            </button>
            <div className="flex flex-col gap-[3px]"><span className="text-[8px] font-bold tracking-[0.14em] text-[#5f7188] max-[760px]:hidden">{section}</span><strong className="text-sm font-semibold">{title}</strong></div>
            <div className="flex-1" />
            <div className="flex items-center gap-2 text-[9px] font-extrabold tracking-[0.12em] text-[#4ade80] max-[760px]:hidden"><i className="h-[7px] w-[7px] rounded-full bg-[var(--green)] shadow-[0_0_0_4px_rgba(34,197,94,0.12)]" /> {connectionStatus === "connected" ? "Data live" : connectionStatus === "connecting" ? "Memuat" : "Terputus"}</div>
            <div className="flex flex-col gap-0.5 border-l border-[var(--border)] pl-[18px] text-right max-[760px]:pl-[10px]">
                <strong className="text-[13px] tabular-nums">{now ? now.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}</strong>
                <span className="text-[9px] uppercase text-[var(--muted)] max-[760px]:hidden">{now ? now.toLocaleDateString("id-ID", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }) : "Memuat waktu"}</span>
                <small>{lastMessageAt ? `Diperbarui ${new Date(lastMessageAt).toLocaleTimeString("id-ID")}` : "Belum ada data"}</small>
            </div>
        </header>
    );
}
