"use client";

import { useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import type { EmissionAnalyticsFilter } from "@/types";
import { fmtDateTimeId } from "@/utils/format";
import { numberDuplicateNames } from "@/utils/emissionAnalytics";
import Select from "@/components/ui/Select";
import { RefreshCw, SlidersHorizontal } from "lucide-react";
import { ANALYTICS_BUTTON_CLASS, ANALYTICS_ERROR_CLASS, ANALYTICS_NOTE_CLASS } from "@/styles/tailwind";

const FILTERS_CLASS = "flex flex-wrap items-end gap-[14px] [&>label]:flex [&>label]:flex-[1_1_160px] [&>label]:flex-col [&>label]:gap-[7px] [&>label]:text-xs [&>label]:text-(--secondary) [&>label>div]:max-w-[340px]";
const DATE_INPUT_CLASS = "min-h-(--control-height) w-full max-w-[340px] rounded-sm border border-[#334155] bg-[#102238] p-(--space-2) text-[#edf5ff] [color-scheme:dark]";

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
    return <section className="mb-[14px] rounded-md border border-(--border) bg-(--surface-sunken)">
        <div className="flex min-h-9 items-center gap-2 border-b border-(--border) px-3 text-[9px] font-bold tracking-[0.12em] text-(--secondary) uppercase">
            <SlidersHorizontal className="h-3.5 w-3.5 text-(--selection)" aria-hidden="true" />
            Lensa analisis
        </div>
        <div className="p-3">
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
            <button type="button" className={`${ANALYTICS_BUTTON_CLASS} inline-flex items-center justify-center gap-2`} onClick={refresh}><RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />Perbarui</button>
        </div>
        <details className="mt-3 border-t border-(--border) pt-2 text-xs text-(--secondary)"><summary className="cursor-pointer py-[7px] font-semibold">Gunakan rentang tanggal & waktu</summary><form action={applyDates} className={`${FILTERS_CLASS} pt-2`}>
            <label>Dari (waktu lokal)<input className={DATE_INPUT_CLASS} required type="datetime-local" name="from" /></label>
            <label>Sampai (waktu lokal)<input className={DATE_INPUT_CLASS} required type="datetime-local" name="to" /></label>
            <button className={ANALYTICS_BUTTON_CLASS} type="submit">Terapkan</button>
        </form></details>
        <p className={ANALYTICS_NOTE_CLASS}>Periode: {fmtDateTimeId(query.from)} – {fmtDateTimeId(query.to)}</p>
        {(rangeError || optionsError) && <p role="alert" className={ANALYTICS_ERROR_CLASS}>{rangeError || optionsError}</p>}
        </div>
    </section>;
}
