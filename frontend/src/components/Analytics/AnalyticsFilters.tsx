"use client";

import { useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import type { EmissionAnalyticsFilter } from "@/types";
import { fmtDateTimeId } from "@/utils/format";
import Select from "@/components/ui/Select";

export default function AnalyticsFilters() {
    const { filter, query, options, optionsError, setFilter, refresh } = useEmissionAnalytics();
    const [rangeError, setRangeError] = useState<string | null>(null);
    const corridors = [...new Map(options.map((s) => [s.corridor_id, s.corridor_name])).entries()];
    const periodOptions = [
        ...(filter.from ? [{ value: "custom", label: "Rentang khusus", disabled: true }] : []),
        ...["1h", "3h", "12h", "24h"].map((value) => ({ value, label: value.replace("h", " jam") })),
    ];
    function applyDates(form: FormData) {
        const start = new Date(String(form.get("from")));
        const end = new Date(String(form.get("to")));
        if (!Number.isFinite(+start) || !Number.isFinite(+end) || start >= end || +end - +start > 31 * 86400000) {
            setRangeError("Pilih rentang waktu yang valid, maksimal 31 hari."); return;
        }
        setRangeError(null);
        setFilter({ from: start.toISOString(), to: end.toISOString() });
    }
    return <div className="page-card analytics-filter-card">
        <div className="analytics-filters">
            <label>Periode<Select ariaLabel="Periode analitik" value={filter.from ? "custom" : filter.timeRange} options={periodOptions}
                onChange={(value) => setFilter({ timeRange: value as EmissionAnalyticsFilter["timeRange"], from: null, to: null })} /></label>
            <label>Koridor<Select ariaLabel="Koridor" value={filter.corridorId ?? ""}
                options={[{ value: "", label: "Semua koridor" }, ...corridors.map(([id, name]) => ({ value: id, label: name }))]}
                onChange={(value) => setFilter({ corridorId: value || null, segmentId: null })} /></label>
            <label>Segmen<Select ariaLabel="Segmen" value={filter.segmentId ?? ""}
                options={[{ value: "", label: "Semua segmen" }, ...options.filter((s) => !filter.corridorId || s.corridor_id === filter.corridorId)
                    .map((s) => ({ value: s.segment_id, label: `${s.segment_name} · ${s.segment_id}` }))]}
                onChange={(value) => setFilter({ segmentId: value || null })} /></label>
            <button type="button" className="analytics-button" onClick={refresh}>Perbarui</button>
        </div>
        <details><summary>Rentang tanggal & waktu</summary><form action={applyDates} className="analytics-filters">
            <label>Dari (waktu lokal)<input required type="datetime-local" name="from" /></label>
            <label>Sampai (waktu lokal)<input required type="datetime-local" name="to" /></label>
            <button className="analytics-button" type="submit">Terapkan</button>
        </form></details>
        <p className="analytics-note">Periode: {fmtDateTimeId(query.from)} – {fmtDateTimeId(query.to)}</p>
        {(rangeError || optionsError) && <p role="alert" className="analytics-error">{rangeError || optionsError}</p>}
    </div>;
}
