"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import Drawer from "@/components/ui/Drawer";
import Select from "@/components/ui/Select";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { numberDuplicateNames } from "@/utils/emissionAnalytics";

export interface HistoryFilters {
    corridorId: string | null;
    segmentId: string | null;
    sourceMode: string | null;
    from: string | null;
    to: string | null;
}
export const EMPTY_HISTORY_FILTERS: HistoryFilters = { corridorId: null, segmentId: null, sourceMode: null, from: null, to: null };

// SYNTHETIC is excluded server-side (dev seed only), so it is intentionally absent.
// REPLAY is the precomputed 54-camera dataset and is selectable.
const SOURCE_OPTIONS = [
    { value: "", label: "Semua sumber" },
    { value: "LIVE", label: "Langsung" },
    { value: "HISTORICAL", label: "Historis" },
    { value: "SNAPSHOT_REAL", label: "Snapshot" },
    { value: "REPLAY", label: "Replay" },
];

function toLocalInput(value: string | null): string {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(+date) ? "" : new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function Category({ title, onReset, children }: { title: string; onReset: () => void; children: ReactNode }) {
    return <div className="drawer-category">
        <div className="drawer-category-head">
            <span>{title}</span>
            <button type="button" className="drawer-reset" aria-label={`Reset ${title}`} onClick={onReset}><RotateCcw aria-hidden="true" /></button>
        </div>
        {children}
    </div>;
}

// Draft state lives here and is only committed on Apply; Cancel/backdrop close
// discards it without touching the applied filters.
export default function HistoryFilterDrawer({ open, filters, onClose, onApply }: {
    open: boolean; filters: HistoryFilters; onClose: () => void; onApply: (next: HistoryFilters) => void;
}) {
    const { options } = useEmissionAnalytics();
    const [draft, setDraft] = useState<HistoryFilters>(filters);
    const [fromText, setFromText] = useState(toLocalInput(filters.from));
    const [toText, setToText] = useState(toLocalInput(filters.to));
    const [dateError, setDateError] = useState<string | null>(null);
    const wasOpen = useRef(false);

    useEffect(() => {
        if (open && !wasOpen.current) {
            setDraft(filters);
            setFromText(toLocalInput(filters.from));
            setToText(toLocalInput(filters.to));
            setDateError(null);
        }
        wasOpen.current = open;
    }, [open, filters]);

    const corridorRows = [...new Map(options.map((segment) => [segment.corridor_id, segment])).values()]
        .sort((a, b) => a.corridor_name.localeCompare(b.corridor_name) || a.corridor_id.localeCompare(b.corridor_id));
    const corridorLabels = numberDuplicateNames(corridorRows.map((segment) => segment.corridor_name));
    const corridors = corridorRows.map((segment, index) => ({ value: segment.corridor_id, label: corridorLabels[index] }));
    const segments = options.filter((segment) => !draft.corridorId || segment.corridor_id === draft.corridorId)
        .map((segment) => ({ value: segment.segment_id, label: `${segment.segment_name} · ${segment.segment_id}` }));

    function clearAll() {
        setDraft(EMPTY_HISTORY_FILTERS);
        setFromText("");
        setToText("");
        setDateError(null);
    }

    function apply() {
        let from = filters.from;
        let to = filters.to;
        if (!fromText || !toText) {
            from = null;
            to = null;
        } else {
            const start = new Date(fromText), end = new Date(toText);
            if (!Number.isFinite(+start) || !Number.isFinite(+end) || start >= end || +end - +start > 31 * 86400000) {
                setDateError("Pilih rentang waktu yang valid, maksimal 31 hari.");
                return;
            }
            from = start.toISOString();
            to = end.toISOString();
        }
        setDateError(null);
        onApply({ ...draft, from, to });
    }

    return <Drawer open={open} title="Filter riwayat" onClose={onClose} footer={<>
        <button type="button" className="analytics-button" onClick={clearAll}>Hapus semua</button>
        <span className="drawer-footer-spacer" />
        <button type="button" className="analytics-button" onClick={onClose}>Batal</button>
        <button type="button" className="analytics-button is-primary" onClick={apply}>Terapkan</button>
    </>}>
        <Category title="Koridor" onReset={() => setDraft((current) => ({ ...current, corridorId: null, segmentId: null }))}>
            <Select ariaLabel="Koridor" searchable searchPlaceholder="Cari koridor…" value={draft.corridorId ?? ""}
                options={[{ value: "", label: "Semua koridor" }, ...corridors]}
                onChange={(value) => setDraft((current) => ({ ...current, corridorId: value || null, segmentId: null }))} />
        </Category>
        <Category title="Segmen" onReset={() => setDraft((current) => ({ ...current, segmentId: null }))}>
            <Select ariaLabel="Segmen" searchable searchPlaceholder="Cari segmen…" value={draft.segmentId ?? ""}
                options={[{ value: "", label: "Semua segmen" }, ...segments]}
                onChange={(value) => setDraft((current) => ({ ...current, segmentId: value || null }))} />
        </Category>
        <Category title="Sumber data" onReset={() => setDraft((current) => ({ ...current, sourceMode: null }))}>
            <Select ariaLabel="Sumber data" value={draft.sourceMode ?? ""} options={SOURCE_OPTIONS}
                onChange={(value) => setDraft((current) => ({ ...current, sourceMode: value || null }))} />
        </Category>
        <Category title="Rentang tanggal" onReset={() => { setFromText(""); setToText(""); setDateError(null); }}>
            <label className="drawer-field">Dari (waktu lokal)
                <input type="datetime-local" value={fromText} onChange={(event) => setFromText(event.target.value)} />
            </label>
            <label className="drawer-field">Sampai (waktu lokal)
                <input type="datetime-local" value={toText} onChange={(event) => setToText(event.target.value)} />
            </label>
            {dateError && <p role="alert" className="analytics-error">{dateError}</p>}
        </Category>
    </Drawer>;
}
