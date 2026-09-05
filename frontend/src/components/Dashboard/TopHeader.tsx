"use client";

import { useEffect, useState } from "react";

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
        <header className="top-header">
            <button className="mobile-menu" onClick={onMenuClick} aria-label="Buka menu">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
            </button>
            <div className="page-heading"><span>{section}</span><strong>{title}</strong></div>
            <div className="header-spacer" />
            <div className={`header-live status-${connectionStatus}`}><i /> {connectionStatus === "connected" ? "TERHUBUNG" : connectionStatus === "connecting" ? "MENGHUBUNGKAN" : "TERPUTUS"}</div>
            <div className="header-time">
                <strong>{now ? now.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}</strong>
                <span>{now ? now.toLocaleDateString("id-ID", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }) : "Memuat waktu"}</span>
                <small>{lastMessageAt ? `Update ${new Date(lastMessageAt).toLocaleTimeString("id-ID")}` : "Belum ada update"}</small>
            </div>
        </header>
    );
}
