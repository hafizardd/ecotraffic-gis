"use client"

import { useEmissionsContext } from "@/context/EmissionsContext"
import { EMISSION_DEFINITIONS } from "@/constants/emissions";

export default function GlobalCounter() {
    const { emissionMap } = useEmissionsContext();

    const totals = Object.fromEntries(EMISSION_DEFINITIONS.map(({ key }) => [key, 0])) as Record<string, number>;
    const totalsKgHr = Object.fromEntries(EMISSION_DEFINITIONS.map(({ key }) => [key, 0])) as Record<string, number>;

    for (const update of emissionMap.values()) {
        for (const { key, field, hourlyField } of EMISSION_DEFINITIONS) {
            totals[key] += Number(update[field] ?? 0);
            totalsKgHr[key] += Number(update[hourlyField] ?? 0);
        }
    }

    const hasData = emissionMap.size > 0;
    return (
        <section className="emissions-bar" aria-label="Ringkasan emisi global">
            <div className="emissions-bar-label"><span>GLOBAL</span><strong>Emisi Saat Ini</strong></div>
            <div className="emissions-summary">
                {hasData ? (
                    EMISSION_DEFINITIONS.map(({ key, label }) => (
                        <div key={key} className={`emission-total pollutant-${key}`}>
                            <span className="summary-label"><span className="pollutant-dot" />{label}</span>
                            <span className="summary-value"><strong>{totals[key].toFixed(1)}</strong><span className="unit">g/min</span></span>
                            <span className="hourly">{totalsKgHr[key].toFixed(1)} kg/hr</span>
                        </div>
                    ))
                ) : (
                    <div className="empty-inline"><span className="loading-spinner small" />Menunggu data emisi real-time...</div>
                )}
            </div>
        </section>
    );
}
