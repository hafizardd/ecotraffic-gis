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
        { label: "CO", gmin: totals.co, kghr: totalsKgHr.co, color: "text-red-500" },
        { label: "NOx", gmin: totals.nox, kghr: totalsKgHr.nox, color: "text-amber-500" },
        { label: "PM", gmin: totals.pm, kghr: totalsKgHr.pm, color: "text-violet-500" },
        { label: "NMVOC", gmin: totals.nmvoc, kghr: totalsKgHr.nmvoc, color: "text-blue-500" },
    ];
    return (
        <div className="fixed top-0 left-0 w-full z-1000 bg-white dark:bg-zinc-900 shadow-md">
            <div className="flex items-center gap-6 px-6 py-3 max-w-screen-2xl justify-center">
                {hasData ? (
                    cards.map(({ label, gmin, kghr, color }) => (
                        <div key={label} className="flex items-baseline gap-2">
                            <span className={`text-sm font-bold ${color}`}>{label}</span>
                            <span className="text-lg font-semibold tabular-nums">
                                {gmin.toFixed(1)}
                            </span>
                            <span className="text-xs text-zinc-400">g/min</span>
                            <span className="text-xs text-zinc-500">
                                ({kghr.toFixed(1)} kg/hr)
                            </span>
                        </div>
                    ))
                ) : (
                    <span className="text-sm text-zinc-400">Waiting for live data...</span>
                )}
            </div>
        </div>
    );
}