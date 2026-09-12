"use client";
import { useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { exportEmissionHistory } from "@/services/api";
import type { AnalyticsQuery } from "@/types";
import { ANALYTICS_BUTTON_CLASS, ANALYTICS_ERROR_CLASS } from "@/styles/tailwind";

// `query` overrides the shared context query so Riwayat's search/tab/source
// filters are reflected in the export, not just the visible table page.
export default function EmissionExport({ query: queryOverride }: { query?: AnalyticsQuery }) {
    const { query: contextQuery } = useEmissionAnalytics();
    const query = queryOverride ?? contextQuery;
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    async function download(format: "csv" | "json") {
        setBusy(true); setError(null);
        try { await exportEmissionHistory(query, format); }
        catch (error) { setError(error instanceof Error ? error.message : "Ekspor gagal"); }
        finally { setBusy(false); }
    }
    return <div className="my-3.5 flex flex-wrap items-center gap-2.5 text-xs text-[#94a3b8]">
        <button className={ANALYTICS_BUTTON_CLASS} disabled={busy} onClick={() => void download("csv")}>{busy ? "Menyiapkan…" : "Ekspor CSV"}</button>
        <button className={ANALYTICS_BUTTON_CLASS} disabled={busy} onClick={() => void download("json")}>Ekspor JSON</button>
        <small>Seluruh hasil sesuai filter, termasuk halaman lain.</small>
        {error && <span role="alert" className={ANALYTICS_ERROR_CLASS}>{error}</span>}
    </div>;
}
