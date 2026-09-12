"use client";

import { useEffect, useState } from "react";
import { Menu } from "lucide-react";

import { useEmissionsContext } from "@/context/EmissionsContext";

export default function TopHeader({ onMenuClick, menuOpen, section, title }: { onMenuClick: () => void; menuOpen: boolean; section: string; title: string }) {
    const [now, setNow] = useState<Date | null>(null);
    const { connectionStatus, lastMessageAt } = useEmissionsContext();
    useEffect(() => {
        const initialTimer = window.setTimeout(() => setNow(new Date()), 0);
        const timer = window.setInterval(() => setNow(new Date()), 1000);
        return () => { window.clearTimeout(initialTimer); window.clearInterval(timer); };
    }, []);

    const connectionLabel = connectionStatus === "connected" ? "Tersambung" : connectionStatus === "connecting" ? "Menghubungkan" : "Terputus";
    const connectionColor = connectionStatus === "connected" ? "text-(--brand-strong)" : connectionStatus === "connecting" ? "text-(--accent)" : "text-(--danger)";

    return (
        <header className="flex min-w-0 items-center gap-4 border-b border-(--border) bg-(--shell) px-5 max-[760px]:gap-3 max-[760px]:px-3">
            <button id="mobile-menu-trigger" type="button" className="hidden h-10 w-10 flex-[0_0_40px] rounded-sm border border-(--border) bg-(--surface) p-2.25 text-(--secondary) transition-colors hover:border-(--contour-strong) hover:text-(--text) max-[760px]:block max-[760px]:h-11 max-[760px]:w-11 max-[760px]:flex-[0_0_44px] [&>svg]:w-full" onClick={onMenuClick} aria-label="Buka menu" aria-controls="primary-navigation" aria-expanded={menuOpen}>
                <Menu aria-hidden="true" />
            </button>
            <div className="flex min-w-0 flex-col"><span className="text-[10px] font-bold tracking-[0.14em] text-(--muted) max-[760px]:hidden">{section}</span><strong className="overflow-hidden text-ellipsis whitespace-nowrap font-(family-name:--font-display) text-[15px] font-semibold tracking-[-0.01em]">{title}</strong></div>
            <div className="flex-1" />
            <div className={`flex items-center gap-2 text-[10px] font-bold tracking-widest uppercase max-[760px]:hidden ${connectionColor}`} role="status" aria-label={`Koneksi data ${connectionLabel}`}><span className="h-1.75 w-1.75 rounded-full bg-current shadow-[0_0_0_4px_rgba(34,197,94,0.1)]" aria-hidden="true" /> Koneksi {connectionLabel}</div>
            <div className="flex min-w-29.5 flex-col border-l border-(--border) pl-4 text-right max-[760px]:min-w-0 max-[760px]:border-0 max-[760px]:pl-0">
                <strong className="font-(family-name:--font-data) text-[13px] leading-4 tabular-nums">{now ? now.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}</strong>
                <span className="text-[10px] leading-4 text-(--muted) max-[760px]:hidden">{lastMessageAt ? `Data ${new Date(lastMessageAt).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : now ? now.toLocaleDateString("id-ID", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }) : "Memuat waktu"}</span>
            </div>
        </header>
    );
}
