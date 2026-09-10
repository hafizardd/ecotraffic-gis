"use client";
import AnalyticsFilters from "../Analytics/AnalyticsFilters";
import EmissionHistory from "../Analytics/EmissionHistory";

export default function RiwayatPage() {
    return <div className="page-container analytics-page"><div className="page-header-section"><span>DATA HISTORIS</span><h1>Riwayat</h1><p>Perhitungan emisi segmen dengan waktu pengamatan, sumber, dan versi perhitungan.</p></div><AnalyticsFilters /><EmissionHistory /></div>;
}
