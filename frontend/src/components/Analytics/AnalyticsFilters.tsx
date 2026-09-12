"use client";

import { useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import type { EmissionAnalyticsFilter } from "@/types";
import { fmtDateTimeId } from "@/utils/format";
import { numberDuplicateNames } from "@/utils/emissionAnalytics";
import Select from "@/components/ui/Select";
import { ANALYTICS_BUTTON_CLASS, ANALYTICS_ERROR_CLASS, ANALYTICS_NOTE_CLASS, PAGE_CARD_CLASS } from "@/styles/tailwind";

const FILTERS_CLASS = "flex flex-wrap items-end gap-[14px] [&>label]:flex [&>label]:flex-[1_1_160px] [&>label]:flex-col [&>label]:gap-[7px] [&>label]:text-xs [&>label]:text-[var(--secondary)] [&>label>div]:max-w-[340px]";
const DATE_INPUT_CLASS = "min-h-[var(--control-height)] w-full max-w-[340px] rounded-[var(--radius-sm)] border border-[#334155] bg-[#102238] p-[var(--space-2)] text-[#edf5ff] [color-scheme:dark]";

export default function AnalyticsFilters() {
    const { filter, query, options, optionsError, setFilter, refresh } = useEmissionAnalytics();
    const [rangeError, setRangeError] = useState<string | null>(null);
    const corridorRows = [...new Map(options.map((segment) => [segment.corridor_id, segment])).values()]
        .sort((a, b) => a.corridor_name.localeCompare(b.corridor_name) || a.corridor_id.localeCompare(b.corridor_id));
    const corridorLabels = numberDuplicateNames(corridorRows.map((segment) => segment.corridor_name));
    const corridors = corridorRows.map((segment, index) => ({ id: segment.corridor_id, name: corridorLabels[index] }));
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
    return <div className={PAGE_CARD_CLASS}>
        <div className={FILTERS_CLASS}>
            <label>Periode<Select ariaLabel="Periode analitik" value={filter.from ? "custom" : filter.timeRange} options={periodOptions}
                onChange={(value) => setFilter({ timeRange: value as EmissionAnalyticsFilter["timeRange"], from: null, to: null })} /></label>
            <label>Koridor<Select ariaLabel="Koridor" searchable searchPlaceholder="Cari koridor…" value={filter.corridorId ?? ""}
                options={[{ value: "", label: "Semua koridor" }, ...corridors.map(({ id, name }) => ({ value: id, label: name }))]}
                onChange={(value) => setFilter({ corridorId: value || null, segmentId: null })} /></label>
            <label>Segmen<Select ariaLabel="Segmen" searchable searchPlaceholder="Cari segmen…" value={filter.segmentId ?? ""}
                options={[{ value: "", label: "Semua segmen" }, ...options.filter((s) => !filter.corridorId || s.corridor_id === filter.corridorId)
                    .map((s) => ({ value: s.segment_id, label: `${s.segment_name} · ${s.segment_id}` }))]}
                onChange={(value) => setFilter({ segmentId: value || null })} /></label>
            <button type="button" className={ANALYTICS_BUTTON_CLASS} onClick={refresh}>Perbarui</button>
        </div>
        <details className="mt-[14px] text-xs text-[#94a3b8]"><summary className="cursor-pointer py-[7px]">Rentang tanggal & waktu</summary><form action={applyDates} className={FILTERS_CLASS}>
            <label>Dari (waktu lokal)<input className={DATE_INPUT_CLASS} required type="datetime-local" name="from" /></label>
            <label>Sampai (waktu lokal)<input className={DATE_INPUT_CLASS} required type="datetime-local" name="to" /></label>
            <button className={ANALYTICS_BUTTON_CLASS} type="submit">Terapkan</button>
        </form></details>
        <p className={ANALYTICS_NOTE_CLASS}>Periode: {fmtDateTimeId(query.from)} – {fmtDateTimeId(query.to)}</p>
        {(rangeError || optionsError) && <p role="alert" className={ANALYTICS_ERROR_CLASS}>{rangeError || optionsError}</p>}
    </div>;
}
