"use client";

import { useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import type { EmissionAnalyticsFilter } from "@/types";
import { fmtDateTimeId } from "@/utils/format";

export default function AnalyticsFilters() {
    const { filter, query, options, optionsError, setFilter, refresh } = useEmissionAnalytics();
    const [rangeError, setRangeError] = useState<string | null>(null);
    const corridors = [...new Map(options.map((s) => [s.corridor_id, s.corridor_name])).entries()];
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
            <label>Periode<select aria-label="Periode analitik" value={filter.from ? "custom" : filter.timeRange} onChange={(e) => setFilter({ timeRange: e.target.value as EmissionAnalyticsFilter["timeRange"], from: null, to: null })}>
                {filter.from && <option value="custom">Rentang khusus</option>}
                {["1h", "3h", "12h", "24h"].map((value) => <option key={value} value={value}>{value.replace("h", " jam")}</option>)}
            </select></label>
            <label>Koridor<select aria-label="Koridor" value={filter.corridorId ?? ""} onChange={(e) => setFilter({ corridorId: e.target.value || null, segmentId: null })}>
                <option value="">Semua koridor</option>{corridors.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </select></label>
            <label>Segmen<select aria-label="Segmen" value={filter.segmentId ?? ""} onChange={(e) => setFilter({ segmentId: e.target.value || null })}>
                <option value="">Semua segmen</option>{options.filter((s) => !filter.corridorId || s.corridor_id === filter.corridorId).map((s) => <option key={s.segment_id} value={s.segment_id}>{s.segment_name} · {s.segment_id}</option>)}
            </select></label>
            <button type="button" className="analytics-button" onClick={refresh}>Perbarui</button>
        </div>
        <details><summary>Rentang tanggal & waktu</summary><form action={applyDates} className="analytics-filters">
            <label>Dari (waktu lokal)<input required type="datetime-local" name="from" /></label>
            <label>Sampai (waktu lokal)<input required type="datetime-local" name="to" /></label>
            <button className="analytics-button" type="submit">Terapkan</button>
        </form></details>
        <p className="analytics-note">{fmtDateTimeId(query.from)} – {fmtDateTimeId(query.to)} · Filter berlaku untuk tren, komposisi, peringkat, riwayat, dan ekspor.</p>
        {(rangeError || optionsError) && <p role="alert" className="analytics-error">{rangeError || optionsError}</p>}
    </div>;
}
