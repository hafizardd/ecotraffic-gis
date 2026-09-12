"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Clock } from "lucide-react";
import { sliderIndex } from "@/utils/activityGrid";
import { fmtDateTimeId } from "@/utils/format";

// Native range input over the static 24h profile. Dragging updates the label
// immediately but debounces the committed hour, so a scrub does not fire a
// request/render per pixel. The date input reuses the same profile for any
// calendar day (the backend maps hour-of-day onto the stored buckets).
export default function ActivityHourSlider({ hours, value, onChange, day, onChangeDay, displayedCount, resolution, aggregated, stale }: {
    hours: string[];
    value: string | null;
    onChange: (hour: string) => void;
    day: string | null;
    onChangeDay: (day: string) => void;
    displayedCount: number;
    resolution: string;
    aggregated: boolean;
    stale: boolean;
}) {
    const index = sliderIndex(hours, value);
    // null = follow the committed value; a number = the in-progress drag.
    const [preview, setPreview] = useState<number | null>(null);
    // Reset the drag preview when the committed hour changes (React's
    // "adjust state during render" pattern instead of an effect).
    const [synced, setSynced] = useState(value);
    if (synced !== value) {
        setSynced(value);
        setPreview(null);
    }
    const commitTimer = useRef<number | null>(null);

    useEffect(() => () => { if (commitTimer.current !== null) window.clearTimeout(commitTimer.current); }, []);

    if (hours.length === 0) return null;

    const commit = (next: number) => {
        if (commitTimer.current !== null) window.clearTimeout(commitTimer.current);
        commitTimer.current = window.setTimeout(() => onChange(hours[next]), 90);
    };
    const handleRange = (event: FormEvent<HTMLInputElement>) => {
        const next = Number(event.currentTarget.value);
        setPreview(next);
        commit(next);
    };
    const selected = Math.min(Math.max(preview ?? index, 0), hours.length - 1);
    const maxDay = new Date().toISOString().slice(0, 10);
    const selectedLabel = fmtDateTimeId(hours[selected]);
    const selectedTime = new Date(hours[selected]).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });

    return (
        <section className="absolute bottom-3 left-1/2 z-20 grid w-[min(650px,calc(100%-320px))] -translate-x-1/2 gap-2 rounded-[var(--radius-md)] border border-[var(--contour-strong)] bg-[rgba(11,32,41,0.94)] px-3 py-2.5 text-[11px] text-[var(--secondary)] shadow-[var(--shadow-float)] backdrop-blur-[10px] max-[980px]:right-3 max-[980px]:left-auto max-[980px]:w-[calc(100%-292px)] max-[980px]:translate-x-0 max-[760px]:right-2 max-[760px]:bottom-2 max-[760px]:left-2 max-[760px]:w-auto" aria-label="Potensi aktivitas per jam" aria-busy={stale}>
            <div className="flex min-w-0 items-center gap-2">
                <label className="flex items-center gap-1.5 font-semibold text-[var(--text)]" htmlFor="activity-hour-slider"><Clock className="h-4 w-4 text-[var(--selection)]" aria-hidden="true" /> Waktu aktivitas</label>
                <span className="h-3 border-l border-[var(--border)]" aria-hidden="true" />
                <output className="font-[var(--font-data)] font-semibold text-[#8edcff] tabular-nums" htmlFor="activity-hour-slider" title={selectedLabel} aria-live="polite">{selectedTime}</output>
                <span className="ml-auto truncate text-[10px] text-[var(--muted)]">
                    {stale ? "Memperbarui grid…" : `${displayedCount} sel · ${resolution}${aggregated ? " · agregat" : ""}`}
                </span>
            </div>
            <div className="grid grid-cols-[minmax(120px,1fr)_auto] items-center gap-3">
                <input
                    id="activity-hour-slider"
                    type="range"
                    min={0}
                    max={hours.length - 1}
                    step={1}
                    value={selected}
                    aria-valuetext={selectedLabel}
                    onInput={handleRange}
                    onChange={handleRange}
                    className="map-range w-full"
                />
                <label className="flex min-h-[var(--control-height)] items-center gap-2 text-[10px] font-semibold text-[var(--muted)]" htmlFor="activity-hour-day"><span className="max-[430px]:sr-only">Tanggal</span>
                    <input id="activity-hour-day" type="date" value={day ?? ""} max={maxDay}
                        className="min-h-[var(--control-height)] rounded-[var(--radius-sm)] border border-[var(--contour-strong)] bg-[var(--surface-raised)] px-2 text-[11px] text-[var(--text)] [color-scheme:dark] hover:border-[var(--selection)]"
                        onChange={(event) => { if (event.target.value) onChangeDay(event.target.value); }} />
                </label>
            </div>
        </section>
    );
}
