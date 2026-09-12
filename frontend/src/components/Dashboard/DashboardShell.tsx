"use client";

import { useCallback, useRef, useState } from "react";
import GlobalCounter from "./GlobalCounter";
import Sidebar from "./Sidebar";
import TopHeader from "./TopHeader";
import EmisiTrenPage from "../Pages/EmisiTrenPage";
import KendaraanPage from "../Pages/KendaraanPage";
import RiwayatPage from "../Pages/RiwayatPage";
import PengaturanPage from "../Pages/PengaturanPage";
import { EmissionAnalyticsProvider } from "@/context/EmissionAnalyticsContext";
import BangJoWidget from "../Chatbot/BangJoWidget";

export type ActiveView = "peta" | "emisi" | "kendaraan" | "riwayat" | "pengaturan";
const viewMeta: Record<ActiveView, [string, string]> = { peta: ["MONITORING DASHBOARD", "Peta Lalu Lintas Real-time"], emisi: ["ANALISIS EMISI", "Emisi & Tren"], kendaraan: ["ANALISIS LALU LINTAS", "Kendaraan"], riwayat: ["DATA HISTORIS", "Riwayat"], pengaturan: ["KONFIGURASI SISTEM", "Pengaturan"] };

export default function DashboardShell({ children }: { children: React.ReactNode }) {
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [mobileNavOpen, setMobileNavOpen] = useState(false);
    const [activeView, setActiveView] = useState<ActiveView>("peta");
    const mainRef = useRef<HTMLElement>(null);
    const analyticsView = activeView === "emisi" || activeView === "riwayat";
    const page = { emisi: <EmisiTrenPage />, kendaraan: <KendaraanPage />, riwayat: <RiwayatPage />, pengaturan: <PengaturanPage /> }[activeView as Exclude<ActiveView, "peta">];
    const changeView = useCallback((view: ActiveView) => {
        setActiveView(view);
        setMobileNavOpen(false);
        window.requestAnimationFrame(() => mainRef.current?.focus());
    }, []);

    return (
        <EmissionAnalyticsProvider><div className="flex h-[100dvh] w-screen bg-(--bg) text-(--text)">
            <a href="#main-content" className="fixed top-2 left-2 z-100 -translate-y-20 rounded-sm bg-(--selection) px-3 py-2 font-semibold text-[#06202b] transition-transform focus:translate-y-0">Langsung ke konten</a>
            <Sidebar
                open={sidebarOpen}
                mobileOpen={mobileNavOpen}
                onToggle={() => setSidebarOpen((value) => !value)}
                onMobileClose={() => setMobileNavOpen(false)}
                activeView={activeView}
                onViewChange={changeView}
            />
            <div className={`grid min-w-0 flex-1 transition-[width] duration-200 ease-out ${analyticsView ? "grid-rows-[56px_minmax(0,1fr)]" : "grid-rows-[56px_auto_minmax(0,1fr)]"}`}>
                <TopHeader onMenuClick={() => setMobileNavOpen(true)} menuOpen={mobileNavOpen} section={viewMeta[activeView][0]} title={viewMeta[activeView][1]} />
                {(activeView === "peta" || activeView === "kendaraan" || activeView === "pengaturan") && <GlobalCounter />}
                <span className="sr-only" role="status" aria-live="polite">Tampilan {viewMeta[activeView][1]}</span>
                <main ref={mainRef} id="main-content" tabIndex={-1} aria-label={viewMeta[activeView][1]} className="min-h-0 min-w-0 overflow-hidden p-3 outline-none max-[760px]:p-2">{activeView === "peta" ? children : page}</main>
            </div>
            <BangJoWidget />
        </div></EmissionAnalyticsProvider>
    );
}
