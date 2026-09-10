"use client";
import { useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { exportEmissionHistory } from "@/services/api";

export default function EmissionExport() {
    const { query } = useEmissionAnalytics();
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    async function download(format: "csv" | "json") {
        setBusy(true); setError(null);
        try { await exportEmissionHistory(query, format); }
        catch (error) { setError(error instanceof Error ? error.message : "Ekspor gagal"); }
        finally { setBusy(false); }
    }
    return <div className="analytics-export">
        <button className="analytics-button" disabled={busy} onClick={() => void download("csv")}>{busy ? "Menyiapkan…" : "Ekspor CSV"}</button>
        <button className="analytics-button" disabled={busy} onClick={() => void download("json")}>Ekspor JSON</button>
        <small>Seluruh hasil sesuai filter, termasuk halaman lain.</small>
        {error && <span role="alert" className="analytics-error">{error}</span>}
    </div>;
}
