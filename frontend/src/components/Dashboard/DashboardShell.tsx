"use client";

import { useState } from "react";
import GlobalCounter from "./GlobalCounter";
import Sidebar from "./Sidebar";
import TopHeader from "./TopHeader";
import EmisiTrenPage from "../Pages/EmisiTrenPage";
import KendaraanPage from "../Pages/KendaraanPage";
import RiwayatPage from "../Pages/RiwayatPage";
import LaporanPage from "../Pages/LaporanPage";
import PengaturanPage from "../Pages/PengaturanPage";

export type ActiveView = "peta" | "emisi" | "kendaraan" | "riwayat" | "laporan" | "pengaturan";
const viewMeta: Record<ActiveView, [string, string]> = { peta: ["MONITORING DASHBOARD", "Peta Lalu Lintas Real-time"], emisi: ["ANALISIS EMISI", "Emisi & Tren"], kendaraan: ["ANALISIS LALU LINTAS", "Kendaraan"], riwayat: ["DATA HISTORIS", "Riwayat"], laporan: ["PELAPORAN", "Laporan"], pengaturan: ["KONFIGURASI SISTEM", "Pengaturan"] };

export default function DashboardShell({ children }: { children: React.ReactNode }) {
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [activeView, setActiveView] = useState<ActiveView>("peta");
    const page = { emisi: <EmisiTrenPage />, kendaraan: <KendaraanPage />, riwayat: <RiwayatPage />, laporan: <LaporanPage />, pengaturan: <PengaturanPage /> }[activeView as Exclude<ActiveView, "peta">];

    return (
        <div className="dashboard-shell">
            <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen((value) => !value)} activeView={activeView} onViewChange={setActiveView} />
            <div className="dashboard-main">
                <TopHeader onMenuClick={() => setSidebarOpen((value) => !value)} section={viewMeta[activeView][0]} title={viewMeta[activeView][1]} />
                <GlobalCounter />
                <main className="dashboard-workspace">{activeView === "peta" ? children : page}</main>
            </div>
        </div>
    );
}
