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
        <EmissionAnalyticsProvider><div className="dashboard-shell">
            <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen((value) => !value)} activeView={activeView} onViewChange={setActiveView} />
            <div className={analyticsView ? "dashboard-main dashboard-main-analytics" : "dashboard-main"}>
                <TopHeader onMenuClick={() => setSidebarOpen((value) => !value)} section={viewMeta[activeView][0]} title={viewMeta[activeView][1]} />
                {(activeView === "peta" || activeView === "kendaraan" || activeView === "pengaturan") && <GlobalCounter />}
                <main className="dashboard-workspace">{activeView === "peta" ? children : page}</main>
            </div>
            <BangJoWidget />
        </div></EmissionAnalyticsProvider>
    );
}
