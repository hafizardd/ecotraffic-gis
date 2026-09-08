"use client";
import useMergedSegments from "@/hooks/useMergedSegments";
import { fmtVehicleId } from "@/utils/format";

const VEHICLES = [
    { key: "car", label: "Car" },
    { key: "motorcycle", label: "Motorcycle" },
    { key: "bus", label: "Bus" },
    { key: "truck", label: "Truck" },
] as const;

export default function KendaraanPage() {
    const { segments } = useMergedSegments();

    const totals: Record<string, number> = { car: 0, motorcycle: 0, bus: 0, truck: 0 };
    let estimated = 0;
    let withVolume = 0;
    for (const s of segments) {
        const v = s.properties.volume_per_hour;
        if (!v) continue;
        withVolume++;
        if (s.properties.volume_status === "estimated") estimated++;
        for (const { key } of VEHICLES) totals[key] += Number(v[key] ?? 0);
    }

    const top = [...segments]
        .filter((s) => s.properties.volume_per_hour)
        .sort((a, b) => {
            const sum = (v: Record<string, number> | null) => (v ? Object.values(v).reduce((x, y) => x + Number(y), 0) : 0);
            return sum(b.properties.volume_per_hour) - sum(a.properties.volume_per_hour);
        })
        .slice(0, 8);

    return (
        <div className="page-container">
            <div className="page-header-section">
                <span>ANALISIS LALU LINTAS</span>
                <h1>Kendaraan</h1>
                <p>{withVolume ? `${withVolume} segmen berdata${estimated ? ` · ${estimated} estimasi CCTV` : ""}` : "Data kendaraan real-time per segmen akan ditampilkan di sini."}</p>
            </div>
            <div className="page-card-grid">
                {VEHICLES.map(({ key, label }) => (
                    <div className="page-card summary-metric" key={key}>
                        <span>{label}</span>
                        <strong>{withVolume === 0 ? "Data tidak tersedia" : `${fmtVehicleId(totals[key])} kend/jam`}</strong>
                        <small>{estimated ? "Termasuk estimasi" : "Agregat segmen"}</small>
                    </div>
                ))}
            </div>
            <div className="page-card">
                <div className="card-header">
                    <strong>Volume per segmen</strong>
                    <span className="unavailable-badge">{top.length ? `${top.length} SEGMEN` : "BELUM TERSEDIA"}</span>
                </div>
                {top.length === 0 ? (
                    <div className="unavailable-state">Belum ada perhitungan volume — data CCTV belum teragregasi.</div>
                ) : (
                    top.map((s) => {
                        const v = s.properties.volume_per_hour ?? {};
                        return (
                            <div key={s.properties.segment_id} className="ranking-row">
                                <strong>{s.properties.name}</strong>
                                <span>{VEHICLES.map(({ key }) => `${key}: ${fmtVehicleId(Number(v[key] ?? 0))}`).join(" · ")}</span>
                                <small>{s.properties.volume_status === "estimated" ? "Estimasi" : "Terukur"} · {String(s.properties.freshness_status ?? "unknown")}</small>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
