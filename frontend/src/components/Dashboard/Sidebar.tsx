"use client";
import { useCallback, useEffect, useRef } from "react";
import { Map, TrendingUp, CarFront, History, ChevronsLeft, ChevronsRight, X } from "lucide-react";
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
    const sidebarRef = useRef<HTMLElement>(null);

    const closeMobileAndRestoreFocus = useCallback(() => {
        onMobileClose();
        window.requestAnimationFrame(() => document.getElementById("mobile-menu-trigger")?.focus());
    }, [onMobileClose]);

    useEffect(() => {
        if (!mobileOpen) return;
        const sidebar = sidebarRef.current;
        const focusables = () => Array.from(sidebar?.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ) ?? []);
        const activeItem = sidebar?.querySelector<HTMLElement>('[aria-current="page"]');
        window.requestAnimationFrame(() => (activeItem ?? focusables()[0])?.focus());
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                event.preventDefault();
                closeMobileAndRestoreFocus();
                return;
            }
            if (event.key !== "Tab") return;
            const items = focusables();
            if (!items.length) return;
            const first = items[0];
            const last = items[items.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        };
        document.addEventListener("keydown", handleKeyDown);
        return () => document.removeEventListener("keydown", handleKeyDown);
    }, [mobileOpen, closeMobileAndRestoreFocus]);

    const copyVisibility = `${open ? "opacity-100" : "pointer-events-none opacity-0"} max-[1100px]:pointer-events-none max-[1100px]:opacity-0 max-[760px]:pointer-events-auto max-[760px]:opacity-100`;
    return (
        <>
        <button type="button" className={`fixed inset-0 z-50 hidden bg-[rgba(3,13,17,0.72)] backdrop-blur-[2px] transition-[opacity,visibility] duration-200 max-[760px]:block ${mobileOpen ? "max-[760px]:visible max-[760px]:pointer-events-auto max-[760px]:opacity-100" : "max-[760px]:invisible max-[760px]:pointer-events-none max-[760px]:opacity-0"}`} aria-label="Tutup menu navigasi" onClick={closeMobileAndRestoreFocus} />
        <aside ref={sidebarRef} id="primary-navigation" role={mobileOpen ? "dialog" : undefined} aria-modal={mobileOpen ? true : undefined} aria-label="Navigasi aplikasi" className={`z-60 flex w-54 flex-[0_0_216px] flex-col overflow-hidden border-r border-(--border) bg-(--sidebar) transition-[width,flex-basis,transform,visibility] duration-200 ease-out max-[1100px]:w-17 max-[1100px]:basis-17 max-[760px]:fixed max-[760px]:inset-y-0 max-[760px]:left-0 max-[760px]:w-54 max-[760px]:basis-54 max-[760px]:shadow-(--shadow-float) ${open ? "" : "w-17 basis-17"} ${mobileOpen ? "max-[760px]:visible max-[760px]:translate-x-0" : "max-[760px]:invisible max-[760px]:-translate-x-full"}`}>
            <div className="flex h-14 flex-[0_0_56px] items-center gap-3 whitespace-nowrap border-b border-(--border) px-4 max-[1100px]:px-3.75 max-[760px]:px-4">
                <div className="relative grid h-9 flex-[0_0_36px] place-items-center"><img src="/bangjo.svg" alt="Bang Jo" className="h-6 w-6" /></div>
                <div className={`flex min-w-0 items-center transition-opacity duration-150 ${copyVisibility}`}><strong className="font-(family-name:--font-display) text-sm font-bold tracking-[-0.01em]">EcoTraffic GIS</strong></div>
                <button type="button" className="ml-auto hidden h-11 w-11 place-items-center rounded-sm border border-(--border) bg-(--surface) text-(--secondary) hover:border-(--contour-strong) hover:text-(--text) max-[760px]:grid" aria-label="Tutup menu" onClick={closeMobileAndRestoreFocus}><X className="h-4.25 w-4.25" aria-hidden="true" /></button>
            </div>
            <nav className="flex flex-col gap-1 px-3 py-4" aria-label="Navigasi utama">
                {navItems.map((item) => (
                    <button key={item.label} type="button" className={`flex min-h-10 cursor-pointer items-center gap-3 whitespace-nowrap rounded-sm border border-transparent bg-transparent px-3 text-(--text-muted) transition-[color,background,border-color] duration-150 ease-out hover:bg-(--surface) hover:text-(--text) max-[760px]:min-h-11 ${activeView === item.view ? "border-[rgba(34,197,94,0.2)]! bg-(--brand-soft)! text-(--brand-strong)! shadow-[inset_3px_0_var(--brand)]" : ""}`} title={item.label} aria-current={activeView === item.view ? "page" : undefined} onClick={() => onViewChange(item.view)}>
                        <item.icon className="h-4.75 w-4.75 flex-[0_0_19px]" strokeWidth={1.8} aria-hidden="true" /><span className={`text-[13px] font-semibold transition-opacity duration-150 ${copyVisibility}`}>{item.label}</span>
                    </button>
                ))}
            </nav>
            <div className="mt-auto border-t border-(--border) p-3 max-[760px]:hidden">
                <button type="button" className="flex min-h-10 w-full cursor-pointer items-center gap-3 whitespace-nowrap rounded-sm border border-transparent bg-transparent px-3 text-(--text-muted) transition-colors duration-150 hover:bg-(--surface) hover:text-(--text) [&>svg]:h-4.5 [&>svg]:w-4.5 [&>svg]:flex-[0_0_18px]" onClick={onToggle} aria-label={open ? "Ciutkan sidebar" : "Buka sidebar"}>
                    {open ? <ChevronsLeft aria-hidden="true" /> : <ChevronsRight aria-hidden="true" />}
                    <span className={`text-[12px] font-semibold transition-opacity duration-150 ${copyVisibility}`}>Ciutkan menu</span>
                </button>
            </div>
        </aside>
        </>
    );
}
