"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Clock } from "lucide-react";
import { sliderIndex } from "@/utils/activityGrid";
import { fmtDateTimeId } from "@/utils/format";

// Native range input over the static 24h profile. Dragging updates the label
// immediately but debounces the committed hour, so a scrub does not fire a
// request/render per pixel. The date input reuses the same profile for any
// calendar day (the backend maps hour-of-day onto the stored buckets).
export default function ActivityHourSlider({ hours, value, onChange, day, onChangeDay }: {
    hours: string[];
    value: string | null;
    onChange: (hour: string) => void;
    day: string | null;
    onChangeDay: (day: string) => void;
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

    return (
        <div className="absolute top-[14px] left-1/2 z-10 flex -translate-x-1/2 items-center gap-[10px] rounded-lg border border-[rgba(148,163,184,0.23)] bg-[rgba(7,20,34,0.9)] px-[14px] py-[7px] text-[10px] font-semibold text-[#dce7f3] shadow-[0_8px_24px_rgba(0,0,0,0.28)] backdrop-blur-[8px] max-[760px]:top-14 [&_label]:flex [&_label]:items-center [&_label]:gap-1.5 [&_svg]:h-3.5 [&_svg]:w-3.5" aria-label="Potensi aktivitas per jam">
            <label htmlFor="activity-hour-slider"><Clock aria-hidden="true" /> Potensi per jam</label>
            <input
                id="activity-hour-slider"
                type="range"
                min={0}
                max={hours.length - 1}
                step={1}
                value={selected}
                onInput={handleRange}
                onChange={handleRange}
                className="w-40 accent-[#38bdf8]"
            />
            <output className="min-w-[120px] text-[#9fc3e0] tabular-nums" htmlFor="activity-hour-slider">{fmtDateTimeId(hours[selected])}</output>
            <label className="text-[#9fc3e0]" htmlFor="activity-hour-day">Tanggal
                <input id="activity-hour-day" type="date" value={day ?? ""} max={maxDay}
                    className="rounded-md border border-[rgba(148,163,184,0.3)] bg-[rgba(15,34,52,0.9)] px-1 py-0.5 text-[10px] text-[#dce7f3] [color-scheme:dark]"
                    onChange={(event) => { if (event.target.value) onChangeDay(event.target.value); }} />
            </label>
        </div>
    );
}
