"use client";

import { useState } from "react";
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
    const [activeView, setActiveView] = useState<ActiveView>("peta");
    const analyticsView = activeView === "emisi" || activeView === "riwayat";
    const page = { emisi: <EmisiTrenPage />, kendaraan: <KendaraanPage />, riwayat: <RiwayatPage />, pengaturan: <PengaturanPage /> }[activeView as Exclude<ActiveView, "peta">];

    return (
        <EmissionAnalyticsProvider><div className="flex h-[100dvh] w-screen bg-[var(--bg)]">
            <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen((value) => !value)} activeView={activeView} onViewChange={setActiveView} />
            <div className={`grid min-w-0 flex-1 transition-[width] duration-250 ease-in-out ${analyticsView ? "grid-rows-[auto_minmax(0,1fr)]" : "grid-rows-[64px_66px_minmax(0,1fr)] max-[760px]:grid-rows-[58px_auto_minmax(0,1fr)]"}`}>
                <TopHeader onMenuClick={() => setSidebarOpen((value) => !value)} section={viewMeta[activeView][0]} title={viewMeta[activeView][1]} />
                {(activeView === "peta" || activeView === "kendaraan" || activeView === "pengaturan") && <GlobalCounter />}
                <main className="min-h-0 min-w-0 overflow-hidden p-3 max-[760px]:p-2">{activeView === "peta" ? children : page}</main>
            </div>
            <BangJoWidget />
        </div></EmissionAnalyticsProvider>
    );
}
