"use client";
import AnalyticsFilters from "../Analytics/AnalyticsFilters";
import HistoryTable from "../Analytics/HistoryTable";
import SectionTitle from "@/components/ui/SectionTitle";

export default function RiwayatPage() {
    return <div className="page-container analytics-page">
        <SectionTitle page eyebrow="Data historis" title="Riwayat" meta="Catatan perhitungan emisi segmen dalam bentuk tabel yang dapat disortir dan diekspor." />
        <AnalyticsFilters />
        <HistoryTable />
    </div>;
}
