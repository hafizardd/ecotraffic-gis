"use client";
import { Map, TrendingUp, CarFront, History, ChevronsLeft, ChevronsRight } from "lucide-react";
import type { ActiveView } from "./DashboardShell";

interface SidebarProps {
    open: boolean;
    onToggle: () => void;
    activeView: ActiveView;
    onViewChange: (view: ActiveView) => void;
}

const navItems = [
    { label: "Peta Live", icon: Map, view: "peta" as const }, { label: "Emisi & Tren", icon: TrendingUp, view: "emisi" as const }, { label: "Kendaraan", icon: CarFront, view: "kendaraan" as const }, { label: "Riwayat", icon: History, view: "riwayat" as const },
];

export default function Sidebar({ open, onToggle, activeView, onViewChange }: SidebarProps) {
    const copyVisibility = `${open ? "opacity-100" : "pointer-events-none opacity-0"} max-[1100px]:pointer-events-none max-[1100px]:opacity-0 max-[760px]:pointer-events-auto max-[760px]:opacity-100`;
    return (
        <aside className={`z-30 flex w-[232px] flex-[0_0_232px] flex-col overflow-hidden border-r border-[var(--border)] bg-[var(--sidebar)] transition-[width,flex-basis,transform] duration-250 ease-in-out max-[1100px]:w-[72px] max-[1100px]:basis-[72px] max-[760px]:fixed max-[760px]:inset-y-0 max-[760px]:left-0 max-[760px]:w-[232px] max-[760px]:basis-[232px] max-[760px]:shadow-[18px_0_50px_rgba(0,0,0,0.45)] ${open ? "max-[760px]:translate-x-0" : "w-[72px] basis-[72px] max-[760px]:-translate-x-full"}`}>
            <div className="flex h-16 items-center gap-[11px] whitespace-nowrap border-b border-[var(--border)] px-[18px]">
                <div className="grid h-9 flex-[0_0_36px] place-items-center rounded-[10px] bg-[linear-gradient(145deg,#1fd267,#0e8f43)] shadow-[0_6px_18px_rgba(34,197,94,0.2)] before:h-[18px] before:w-[18px] before:-rotate-[25deg] before:rounded-[50%_50%_50%_10%] before:border-2 before:border-white before:content-['']" aria-hidden="true"><span /></div>
                <div className={`flex flex-col gap-[3px] transition-opacity duration-150 ${copyVisibility}`}><strong className="text-sm tracking-[0.01em]">EcoTraffic GIS</strong><span className="text-[9px] tracking-[0.04em] text-[var(--muted)]">Smart Emission Monitoring</span></div>
            </div>
            <nav className="flex flex-col gap-[5px] px-3 py-5" aria-label="Navigasi utama">
                {navItems.map((item) => (
                    <button key={item.label} className={`flex min-h-[42px] cursor-pointer items-center gap-[13px] whitespace-nowrap rounded-lg border-0 bg-transparent px-[13px] text-[#6f8197] transition-all duration-180 ease-in-out hover:bg-[#102238] hover:text-[#dbe7f4] ${activeView === item.view ? "bg-[rgba(34,197,94,0.1)]! text-[#43d978]! shadow-[inset_3px_0_#22c55e]" : ""}`} title={!open ? item.label : undefined} onClick={() => onViewChange(item.view)}>
                        <item.icon className="h-5 w-5 flex-[0_0_20px]" aria-hidden="true" /><span className={`text-xs font-semibold transition-opacity duration-150 ${copyVisibility}`}>{item.label}</span>
                    </button>
                ))}
            </nav>
            <div className="mt-auto border-t border-[var(--border)] p-3">
                <button className="mt-[7px] flex min-h-[42px] w-full cursor-pointer items-center gap-[13px] whitespace-nowrap rounded-lg border-0 bg-transparent px-[13px] text-[#6f8197] transition-all duration-180 ease-in-out hover:bg-[#102238] hover:text-[#dbe7f4] [&>svg]:h-[19px] [&>svg]:w-[19px] [&>svg]:flex-[0_0_19px]" onClick={onToggle} aria-label={open ? "Ciutkan sidebar" : "Buka sidebar"}>
                    {open ? <ChevronsLeft aria-hidden="true" /> : <ChevronsRight aria-hidden="true" />}
                    <span className={`text-xs font-semibold transition-opacity duration-150 ${copyVisibility}`}>Ciutkan menu</span>
                </button>
            </div>
        </aside>
    );
}
