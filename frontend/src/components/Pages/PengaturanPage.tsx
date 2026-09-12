"use client";
import SectionTitle from "@/components/ui/SectionTitle";
import { PAGE_CARD_CLASS, PAGE_CONTAINER_CLASS } from "@/styles/tailwind";

const settings = ["Bobot penilaian", "Faktor emisi", "Pipeline kalkulasi", "Manajemen kamera dan sumber"];

export default function PengaturanPage() {
    return <div className={PAGE_CONTAINER_CLASS}>
        <SectionTitle page eyebrow="Konfigurasi sistem" title="Pengaturan" meta="Konfigurasi berikut bersifat read-only sampai backend settings tersedia." />
        <div className="grid max-w-190 gap-2.25">{settings.map((item) => <div className={`${PAGE_CARD_CLASS} m-0 flex items-center justify-between`} key={item}><div className="flex flex-col gap-1.25"><strong className="text-[11px]">{item}</strong><span className="text-[9px] text-(--muted)">Konfigurasi belum tersedia</span></div><span className="inline-flex w-max items-center rounded-[5px] bg-[rgba(148,163,184,0.1)] px-1.75 py-1 text-[8px] font-extrabold tracking-[0.06em] text-(--secondary) uppercase">READ-ONLY</span></div>)}</div>
    </div>;
}
