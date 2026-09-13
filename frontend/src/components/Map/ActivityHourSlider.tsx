"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Clock, Pause, Play } from "lucide-react";
import { sliderIndex } from "@/utils/activityGrid";
import { fmtDateTimeId } from "@/utils/format";
import type { ActivityTimeMode } from "@/types";

const PLAY_INTERVAL_MS = 1000;

const TIME_MODES: { key: ActivityTimeMode; label: string }[] = [
    { key: "live", label: "Live" },
    { key: "replay", label: "Replay" },
];

// Bottom activity bar. In replay it is a native range input over the static 24h
// profile (drag debounces the committed hour; play auto-advances left to right).
// In live the slider is replaced by a live indicator: the grid reads each
// segment's newest observed fact and repolls, so there is no hour to scrub.
export default function ActivityHourSlider({ hours, value, onChange, day, onChangeDay, displayedCount, resolution, aggregated, stale, timeMode, onTimeModeChange, updatedAt }: {
    hours: string[];
    value: string | null;
    onChange: (hour: string) => void;
    day: string | null;
    onChangeDay: (day: string) => void;
    displayedCount: number;
    resolution: string;
    aggregated: boolean;
    stale: boolean;
    timeMode: ActivityTimeMode;
    onTimeModeChange: (mode: ActivityTimeMode) => void;
    updatedAt: string | null;
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

    const [playing, setPlaying] = useState(false);
    const last = hours.length - 1;
    const selected = Math.min(Math.max(preview ?? index, 0), Math.max(last, 0));

    // One hour per tick, left to right; stop when the rightmost hour is reached.
    // Rescheduling on `selected` (a timeout, not an interval) keeps the next step
    // visually aligned with the hour that was just committed.
    useEffect(() => {
        if (!playing) return;
        const timer = window.setTimeout(() => {
            const next = selected + 1;
            if (next > last) {
                setPlaying(false);
                return;
            }
            setPreview(next);
            onChange(hours[next]);
        }, PLAY_INTERVAL_MS);
        return () => window.clearTimeout(timer);
    }, [playing, selected, last, hours, onChange]);

    if (timeMode === "replay" && hours.length === 0) return null;

    const commit = (next: number) => {
        if (commitTimer.current !== null) window.clearTimeout(commitTimer.current);
        commitTimer.current = window.setTimeout(() => onChange(hours[next]), 90);
    };
    const handleRange = (event: FormEvent<HTMLInputElement>) => {
        if (playing) setPlaying(false);
        const next = Number(event.currentTarget.value);
        setPreview(next);
        commit(next);
    };
    const togglePlay = () => {
        if (playing) {
            setPlaying(false);
            return;
        }
        if (selected >= last) {
            setPreview(0);
            onChange(hours[0]);
        }
        setPlaying(true);
    };
    const maxDay = new Date().toISOString().slice(0, 10);
    const selectedLabel = hours.length > 0 ? fmtDateTimeId(hours[selected]) : "";
    const selectedTime = hours.length > 0 ? new Date(hours[selected]).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }) : "";
    const liveUpdated = updatedAt ? new Date(updatedAt).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : null;
    const status = stale
        ? "Memperbarui grid…"
        : `${displayedCount} sel · ${resolution}${aggregated ? " · agregat" : ""}${timeMode === "live" && liveUpdated ? ` · ${liveUpdated}` : ""}`;

    return (
        <section className="absolute bottom-3 left-1/2 z-20 grid w-[min(650px,calc(100%-320px))] -translate-x-1/2 gap-2 rounded-md border border-(--contour-strong) bg-[rgba(11,32,41,0.94)] px-3 py-2.5 text-[11px] text-(--secondary) shadow-(--shadow-float) backdrop-blur-[10px] max-[980px]:right-3 max-[980px]:left-auto max-[980px]:w-[calc(100%-292px)] max-[980px]:translate-x-0 max-[760px]:right-2 max-[760px]:bottom-2 max-[760px]:left-2 max-[760px]:w-auto" aria-label="Potensi aktivitas per jam" aria-busy={stale}>
            <div className="flex min-w-0 items-center gap-2">
                <div className="inline-flex items-center rounded-sm bg-[rgba(9,26,34,0.72)] p-0.5" role="tablist" aria-label="Mode waktu potensi aktivitas">
                    {TIME_MODES.map(({ key, label }) => (
                        <button
                            key={key}
                            type="button"
                            role="tab"
                            aria-selected={timeMode === key}
                            className={`cursor-pointer rounded-[5px] border border-transparent px-2.5 py-1 text-[10px] font-semibold transition-colors ${timeMode === key ? "border-[rgba(56,189,248,0.32)] bg-(--selection-soft) text-[#8edcff]" : "text-(--text-muted) hover:bg-(--surface) hover:text-(--text)"}`}
                            onClick={() => onTimeModeChange(key)}
                        >
                            {label}
                        </button>
                    ))}
                </div>
                {timeMode === "replay" ? (
                    <>
                        <label className="flex items-center gap-1.5 font-semibold text-(--text)" htmlFor="activity-hour-slider"><Clock className="h-4 w-4 text-(--selection)" aria-hidden="true" /> Waktu aktivitas</label>
                        {last >= 1 && (
                            <button type="button" className="grid h-6 w-6 cursor-pointer place-items-center rounded-[6px] border border-[color:rgba(148,163,184,0.3)] bg-[rgba(15,34,52,0.9)] text-[#dce7f3] hover:border-(--selection) [&>svg]:h-3.25 [&>svg]:w-3.25" onClick={togglePlay}
                                aria-label={playing ? "Jeda" : "Putar"} title={playing ? "Jeda" : "Putar"}>
                                {playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
                            </button>
                        )}
                        <span className="h-3 border-l border-(--border)" aria-hidden="true" />
                        <output className="font-(family-name:--font-data) font-semibold text-[#8edcff] tabular-nums" htmlFor="activity-hour-slider" title={selectedLabel} aria-live="polite">{selectedTime}</output>
                    </>
                ) : (
                    <span className="flex items-center gap-1.5 font-semibold text-(--text)">
                        <i className="h-1.5 w-1.5 rounded-full bg-(--green) shadow-[0_0_0_3px_rgba(34,197,94,0.12)]" aria-hidden="true" />
                        Live
                    </span>
                )}
                <span className="ml-auto truncate text-[10px] text-(--muted)">{status}</span>
            </div>
            {timeMode === "replay" && (
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
                    <label className="flex min-h-(--control-height) items-center gap-2 text-[10px] font-semibold text-(--muted)" htmlFor="activity-hour-day"><span className="max-[430px]:sr-only">Tanggal</span>
                        <input id="activity-hour-day" type="date" value={day ?? ""} max={maxDay}
                            className="min-h-(--control-height) rounded-sm border border-(--contour-strong) bg-(--surface-raised) px-2 text-[11px] text-(--text) [color-scheme:dark] hover:border-(--selection)"
                            onChange={(event) => { if (event.target.value) onChangeDay(event.target.value); }} />
                    </label>
                </div>
            )}
        </section>
    );
}
