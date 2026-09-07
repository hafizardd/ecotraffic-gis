"use client";
import { Map, TrendingUp, CarFront, History, FileText, Settings, ChevronsLeft, ChevronsRight } from "lucide-react";
import type { ActiveView } from "./DashboardShell";

interface SidebarProps {
    open: boolean;
    onToggle: () => void;
    activeView: ActiveView;
    onViewChange: (view: ActiveView) => void;
}

const navItems = [
    { label: "Peta Live", icon: Map, view: "peta" as const }, { label: "Emisi & Tren", icon: TrendingUp, view: "emisi" as const }, { label: "Kendaraan", icon: CarFront, view: "kendaraan" as const }, { label: "Riwayat", icon: History, view: "riwayat" as const }, { label: "Laporan", icon: FileText, view: "laporan" as const }, { label: "Pengaturan", icon: Settings, view: "pengaturan" as const },
];

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
                        <item.icon className="nav-icon" aria-hidden="true" /><span>{item.label}</span>
                    </button>
                ))}
            </nav>
            <div className="sidebar-footer">
                <div className="system-status" title={!open ? "Status pipeline" : undefined}>
                    <i /><div><strong>PIPELINE</strong><span>Status tersedia di header</span></div>
                </div>
                <button className="sidebar-toggle" onClick={onToggle} aria-label={open ? "Ciutkan sidebar" : "Buka sidebar"}>
                    {open ? <ChevronsLeft aria-hidden="true" /> : <ChevronsRight aria-hidden="true" />}
                    <span>Ciutkan menu</span>
                </button>
            </div>
        </aside>
    );
}
