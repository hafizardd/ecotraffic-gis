"use client";
import SectionTitle from "@/components/ui/SectionTitle";

const settings = ["Bobot penilaian", "Faktor emisi", "Pipeline kalkulasi", "Manajemen kamera dan sumber"];

export default function PengaturanPage() {
    return <div className="page-container">
        <SectionTitle page eyebrow="Konfigurasi sistem" title="Pengaturan" meta="Konfigurasi berikut bersifat read-only sampai backend settings tersedia." />
        <div className="settings-grid">{settings.map((item) => <div className="page-card setting-row" key={item}><div><strong>{item}</strong><span>Konfigurasi belum tersedia</span></div><span className="readonly-badge">READ-ONLY</span></div>)}</div>
    </div>;
}
