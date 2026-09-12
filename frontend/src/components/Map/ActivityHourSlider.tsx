"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Clock, Pause, Play } from "lucide-react";
import { sliderIndex } from "@/utils/activityGrid";
import { fmtDateTimeId } from "@/utils/format";

const PLAY_INTERVAL_MS = 1000;

// Native range input over the static 24h profile. Dragging updates the label
// immediately but debounces the committed hour, so a scrub does not fire a
// request/render per pixel. The date input reuses the same profile for any
// calendar day (the backend maps hour-of-day onto the stored buckets). The play
// button auto-advances left to right, stopping at the rightmost hour.
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
    const [playing, setPlaying] = useState(false);
    const last = hours.length - 1;
    const selected = Math.min(Math.max(preview ?? index, 0), Math.max(last, 0));
    const commitTimer = useRef<number | null>(null);

    useEffect(() => () => { if (commitTimer.current !== null) window.clearTimeout(commitTimer.current); }, []);

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

    if (hours.length === 0) return null;

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

    return (
        <div className="map-hour-slider" aria-label="Potensi aktivitas per jam">
            <label htmlFor="activity-hour-slider"><Clock aria-hidden="true" /> Potensi per jam</label>
            {last >= 1 && (
                <button type="button" className="map-hour-play" onClick={togglePlay}
                    aria-label={playing ? "Jeda" : "Putar"} title={playing ? "Jeda" : "Putar"}>
                    {playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
                </button>
            )}
            <input
                id="activity-hour-slider"
                type="range"
                min={0}
                max={last}
                step={1}
                value={selected}
                onInput={handleRange}
                onChange={handleRange}
            />
            <output htmlFor="activity-hour-slider">{fmtDateTimeId(hours[selected])}</output>
            <label className="map-hour-day" htmlFor="activity-hour-day">Tanggal
                <input id="activity-hour-day" type="date" value={day ?? ""} max={maxDay}
                    onChange={(event) => { if (event.target.value) onChangeDay(event.target.value); }} />
            </label>
        </div>
    );
}
