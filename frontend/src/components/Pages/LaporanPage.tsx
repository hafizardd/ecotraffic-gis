"use client";
import AnalyticsFilters from "../Analytics/AnalyticsFilters";
import EmissionHistory from "../Analytics/EmissionHistory";

export default function LaporanPage() {
    return <div className="page-container analytics-page"><div className="page-header-section"><span>PELAPORAN</span><h1>Laporan & Ekspor</h1><p>Unduh CSV atau JSON dari hasil historis sesuai filter. Tinjau data dan jejak sumber sebelum ekspor.</p></div><AnalyticsFilters /><EmissionHistory /></div>;
}
