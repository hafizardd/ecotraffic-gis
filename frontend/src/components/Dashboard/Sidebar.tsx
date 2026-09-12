"use client";
import { useEffect } from "react";
import { Map, TrendingUp, CarFront, History, ChevronsLeft, ChevronsRight, Waypoints, X } from "lucide-react";
import type { ActiveView } from "./DashboardShell";

interface SidebarProps {
    open: boolean;
    mobileOpen: boolean;
    onToggle: () => void;
    onMobileClose: () => void;
    activeView: ActiveView;
    onViewChange: (view: ActiveView) => void;
}

const navItems = [
    { label: "Peta Live", icon: Map, view: "peta" as const }, { label: "Emisi & Tren", icon: TrendingUp, view: "emisi" as const }, { label: "Kendaraan", icon: CarFront, view: "kendaraan" as const }, { label: "Riwayat", icon: History, view: "riwayat" as const },
];

export default function Sidebar({ open, mobileOpen, onToggle, onMobileClose, activeView, onViewChange }: SidebarProps) {
    useEffect(() => {
        if (!mobileOpen) return;
        const closeOnEscape = (event: KeyboardEvent) => {
            if (event.key === "Escape") onMobileClose();
        };
        document.addEventListener("keydown", closeOnEscape);
        return () => document.removeEventListener("keydown", closeOnEscape);
    }, [mobileOpen, onMobileClose]);

    const copyVisibility = `${open ? "opacity-100" : "pointer-events-none opacity-0"} max-[1100px]:pointer-events-none max-[1100px]:opacity-0 max-[760px]:pointer-events-auto max-[760px]:opacity-100`;
    return (
        <>
        <button type="button" className={`fixed inset-0 z-[50] hidden bg-[rgba(3,13,17,0.72)] backdrop-blur-[2px] transition-[opacity,visibility] duration-200 max-[760px]:block ${mobileOpen ? "max-[760px]:visible max-[760px]:pointer-events-auto max-[760px]:opacity-100" : "max-[760px]:invisible max-[760px]:pointer-events-none max-[760px]:opacity-0"}`} aria-label="Tutup menu navigasi" onClick={onMobileClose} />
        <aside id="primary-navigation" aria-label="Navigasi aplikasi" className={`z-[60] flex w-[216px] flex-[0_0_216px] flex-col overflow-hidden border-r border-[var(--border)] bg-[var(--sidebar)] transition-[width,flex-basis,transform,visibility] duration-200 ease-out max-[1100px]:w-[68px] max-[1100px]:basis-[68px] max-[760px]:fixed max-[760px]:inset-y-0 max-[760px]:left-0 max-[760px]:w-[216px] max-[760px]:basis-[216px] max-[760px]:shadow-[var(--shadow-float)] ${open ? "" : "w-[68px] basis-[68px]"} ${mobileOpen ? "max-[760px]:visible max-[760px]:translate-x-0" : "max-[760px]:invisible max-[760px]:-translate-x-full"}`}>
            <div className="flex h-14 flex-[0_0_56px] items-center gap-3 whitespace-nowrap border-b border-[var(--border)] px-4 max-[1100px]:px-[15px] max-[760px]:px-4">
                <div className="relative grid h-9 flex-[0_0_36px] place-items-center rounded-[var(--radius-md)] border border-[rgba(74,222,128,0.35)] bg-[var(--surface-raised)] text-[var(--brand-strong)] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.025)] after:absolute after:right-[5px] after:bottom-[5px] after:h-1.5 after:w-1.5 after:rounded-full after:bg-[var(--brand)] after:shadow-[0_0_0_3px_rgba(34,197,94,0.13)] after:content-['']" aria-hidden="true"><Waypoints className="h-[19px] w-[19px]" /></div>
                <div className={`flex min-w-0 flex-col transition-opacity duration-150 ${copyVisibility}`}><strong className="font-[var(--font-display)] text-sm font-bold tracking-[-0.01em]">EcoTraffic GIS</strong><span className="mt-px text-[10px] tracking-[0.055em] text-[var(--muted)] uppercase">docker compose up -d --build postgres redis backend frontendlas</span></div>
                <button type="button" className="ml-auto hidden h-9 w-9 place-items-center rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] text-[var(--secondary)] hover:border-[var(--contour-strong)] hover:text-[var(--text)] max-[760px]:grid" aria-label="Tutup menu" onClick={onMobileClose}><X className="h-[17px] w-[17px]" aria-hidden="true" /></button>
            </div>
            <nav className="flex flex-col gap-1 px-3 py-4" aria-label="Navigasi utama">
                {navItems.map((item) => (
                    <button key={item.label} type="button" className={`flex min-h-10 cursor-pointer items-center gap-3 whitespace-nowrap rounded-[var(--radius-sm)] border border-transparent bg-transparent px-3 text-[var(--text-muted)] transition-[color,background,border-color] duration-150 ease-out hover:bg-[var(--surface)] hover:text-[var(--text)] max-[760px]:min-h-11 ${activeView === item.view ? "border-[rgba(34,197,94,0.2)]! bg-[var(--brand-soft)]! text-[var(--brand-strong)]! shadow-[inset_3px_0_var(--brand)]" : ""}`} title={!open ? item.label : undefined} aria-current={activeView === item.view ? "page" : undefined} onClick={() => onViewChange(item.view)}>
                        <item.icon className="h-[19px] w-[19px] flex-[0_0_19px]" strokeWidth={1.8} aria-hidden="true" /><span className={`text-[13px] font-semibold transition-opacity duration-150 ${copyVisibility}`}>{item.label}</span>
                    </button>
                ))}
            </nav>
            <div className="mt-auto border-t border-[var(--border)] p-3 max-[760px]:hidden">
                <button type="button" className="flex min-h-10 w-full cursor-pointer items-center gap-3 whitespace-nowrap rounded-[var(--radius-sm)] border border-transparent bg-transparent px-3 text-[var(--text-muted)] transition-colors duration-150 hover:bg-[var(--surface)] hover:text-[var(--text)] [&>svg]:h-[18px] [&>svg]:w-[18px] [&>svg]:flex-[0_0_18px]" onClick={onToggle} aria-label={open ? "Ciutkan sidebar" : "Buka sidebar"}>
                    {open ? <ChevronsLeft aria-hidden="true" /> : <ChevronsRight aria-hidden="true" />}
                    <span className={`text-[12px] font-semibold transition-opacity duration-150 ${copyVisibility}`}>Ciutkan menu</span>
                </button>
            </div>
        </aside>
        </>
    );
}
