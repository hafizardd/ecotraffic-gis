"use client";
import HistoryTable from "../Analytics/HistoryTable";
import SectionTitle from "@/components/ui/SectionTitle";
import { PAGE_CONTAINER_CLASS } from "@/styles/tailwind";

export default function RiwayatPage() {
    return <div className={`${PAGE_CONTAINER_CLASS} [&_:focus-visible]:outline-2 [&_:focus-visible]:outline-offset-3 [&_:focus-visible]:outline-[#22c55e]`}>
        <SectionTitle page eyebrow="Data historis" title="Riwayat" meta="Catatan perhitungan emisi segmen dalam bentuk tabel yang dapat disortir dan diekspor." />
        <HistoryTable />
    </div>;
}
