"use client";

import { Clock } from "lucide-react";
import { sliderIndex } from "@/utils/activityGrid";
import { fmtDateTimeId } from "@/utils/format";

// Native range input over the available hour buckets; hidden entirely when the
// backend reported no data in the last 24h. The track spans only available
// hours, so gaps are unreachable rather than dragging into an empty hour.
export default function ActivityHourSlider({ hours, value, onChange }: {
    hours: string[];
    value: string | null;
    onChange: (hour: string) => void;
}) {
    if (hours.length === 0) return null;
    const index = sliderIndex(hours, value);
    // onInput fires on every drag tick. onChange is kept on the controlled input
    // because React requires it, and it fires on the same native event; both
    // resolve to the same hour so the state update stays idempotent.
    const commit = (input: HTMLInputElement) => onChange(hours[Number(input.value)]);
    return (
        <div className="map-hour-slider" aria-label="Potensi aktivitas per jam">
            <label htmlFor="activity-hour-slider"><Clock aria-hidden="true" /> Potensi per jam</label>
            <input
                id="activity-hour-slider"
                type="range"
                min={0}
                max={hours.length - 1}
                step={1}
                value={index}
                onInput={(event) => commit(event.currentTarget)}
                onChange={(event) => commit(event.currentTarget)}
            />
            <output htmlFor="activity-hour-slider">{fmtDateTimeId(hours[index])}</output>
        </div>
    );
}
