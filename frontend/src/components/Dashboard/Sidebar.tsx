"use client";
import type { ActiveView } from "./DashboardShell";

interface SidebarProps {
    open: boolean;
    onToggle: () => void;
    activeView: ActiveView;
    onViewChange: (view: ActiveView) => void;
}

const navItems = [
    { label: "Peta Live", icon: "map", view: "peta" as const }, { label: "Emisi & Tren", icon: "trend", view: "emisi" as const }, { label: "Kendaraan", icon: "car", view: "kendaraan" as const }, { label: "Riwayat", icon: "history", view: "riwayat" as const }, { label: "Laporan", icon: "report", view: "laporan" as const }, { label: "Pengaturan", icon: "settings", view: "pengaturan" as const },
];

function NavIcon({ name }: { name: string }) {
    const paths: Record<string, React.ReactNode> = {
        map: <><path d="m3 6 5-2 8 3 5-2v13l-5 2-8-3-5 2Z"/><path d="M8 4v13M16 7v13"/></>,
        trend: <><path d="M4 19V5M4 19h16"/><path d="m7 15 4-5 3 3 5-7"/></>,
        car: <><path d="M5 17h14a2 2 0 0 0 2-2v-3l-2-5H5l-2 5v3a2 2 0 0 0 2 2Z"/><path d="M7 17v2M17 17v2M3 12h18"/></>,
        history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></>,
        report: <><path d="M6 3h9l3 3v15H6Z"/><path d="M14 3v4h4M9 12h6M9 16h6"/></>,
        settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></>,
    };
    return <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

export default function Sidebar({ open, onToggle, activeView, onViewChange }: SidebarProps) {
    return (
        <aside className={`sidebar ${open ? "sidebar-open" : "sidebar-collapsed"}`}>
            <div className="brand">
                <div className="brand-mark" aria-hidden="true"><span /></div>
                <div className="brand-copy"><strong>EcoTraffic GIS</strong><span>Smart Emission Monitoring</span></div>
            </div>
            <nav className="sidebar-nav" aria-label="Navigasi utama">
                {navItems.map((item) => (
                    <button key={item.label} className={`nav-item ${activeView === item.view ? "active" : ""}`} title={!open ? item.label : undefined} onClick={() => onViewChange(item.view)}>
                        <NavIcon name={item.icon} /><span>{item.label}</span>
                    </button>
                ))}
            </nav>
            <div className="sidebar-footer">
                <div className="system-status" title={!open ? "Status pipeline" : undefined}>
                    <i /><div><strong>PIPELINE</strong><span>Status tersedia di header</span></div>
                </div>
                <button className="sidebar-toggle" onClick={onToggle} aria-label={open ? "Ciutkan sidebar" : "Buka sidebar"}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d={open ? "m15 18-6-6 6-6" : "m9 18 6-6-6-6"}/></svg>
                    <span>Ciutkan menu</span>
                </button>
            </div>
        </aside>
    );
}
