"use client"

import { useEmissionsContext } from "@/context/EmissionsContext"

export default function GlobalCounter() {
    const emissionMap = useEmissionsContext();

    const totals = {
        co: 0,
        nox: 0,
        pm: 0,
        nmvoc: 0
    }

    const totalsKgHr = {
        co: 0,
        nox: 0,
        pm: 0,
        nmvoc: 0
    }

    for (const update of emissionMap.values()) {
        totals.co += update.total_co_g_per_min;
        totals.nox += update.total_nox_g_per_min;
        totals.pm += update.total_pm_g_per_min;
        totals.nmvoc += update.total_nmvoc_g_per_min;

        totalsKgHr.co += update.total_co_kg_per_hr;
        totalsKgHr.nox += update.total_nox_kg_per_hr;
        totalsKgHr.pm += update.total_pm_kg_per_hr;
        totalsKgHr.nmvoc += update.total_nmvoc_kg_per_hr;
    }

    const hasData = emissionMap.size > 0;
    const cards = [
        { label: "CO", gmin: totals.co, kghr: totalsKgHr.co, tone: "co" },
        { label: "NOx", gmin: totals.nox, kghr: totalsKgHr.nox, tone: "nox" },
        { label: "PM", gmin: totals.pm, kghr: totalsKgHr.pm, tone: "pm" },
        { label: "NMVOC", gmin: totals.nmvoc, kghr: totalsKgHr.nmvoc, tone: "nmvoc" },
    ];
    return (
        <section className="emissions-bar" aria-label="Ringkasan emisi global">
            <div className="emissions-bar-label"><span>GLOBAL</span><strong>Emisi Saat Ini</strong></div>
            <div className="emissions-summary">
                {hasData ? (
                    cards.map(({ label, gmin, kghr, tone }) => (
                        <div key={label} className={`emission-total pollutant-${tone}`}>
                            <span className="pollutant-dot" /><span className="emission-label">{label}</span>
                            <strong>{gmin.toFixed(1)}</strong><span className="unit">g/min</span>
                            <span className="hourly">{kghr.toFixed(1)} kg/hr</span>
                        </div>
                    ))
                ) : (
                    <div className="empty-inline"><span className="loading-spinner small" />Menunggu data emisi real-time...</div>
                )}
            </div>
        </section>
    );
}
