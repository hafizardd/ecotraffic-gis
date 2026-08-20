"use client";

import { useState } from "react";
import GlobalCounter from "./GlobalCounter";
import Sidebar from "./Sidebar";
import TopHeader from "./TopHeader";

export default function DashboardShell({ children }: { children: React.ReactNode }) {
    const [sidebarOpen, setSidebarOpen] = useState(true);

    return (
        <div className="dashboard-shell">
            <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen((value) => !value)} />
            <div className="dashboard-main">
                <TopHeader onMenuClick={() => setSidebarOpen((value) => !value)} />
                <GlobalCounter />
                <main className="dashboard-workspace">{children}</main>
            </div>
        </div>
    );
}
