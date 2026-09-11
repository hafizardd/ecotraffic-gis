"use client";
import { useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { deleteEmissionHistory } from "@/services/api";
import { fmtIntId } from "@/utils/format";
import type { AnalyticsQuery } from "@/types";

type Scope = "beyond" | "page";

export default function EmissionBulkDelete({ query: queryOverride, page, pageSize = 25, totalPages, sort, order, onDeleted }: {
    query?: AnalyticsQuery; page: number; pageSize?: number; totalPages: number; sort: string; order: "asc" | "desc"; onDeleted: () => void;
}) {
    const { query: contextQuery } = useEmissionAnalytics();
    const query = queryOverride ?? contextQuery;
    const [scope, setScope] = useState<Scope>("beyond");
    const [targetText, setTargetText] = useState(String(page));
    const [lastPage, setLastPage] = useState(page);
    const [matched, setMatched] = useState<number | null>(null);
    const [result, setResult] = useState<number | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    if (page !== lastPage) { setLastPage(page); setTargetText(String(page)); setMatched(null); }

    function clamp(value: number): number {
        const candidate = Number.isFinite(value) && value >= 1 ? Math.floor(value) : 1;
        return scope === "page" ? Math.min(candidate, totalPages) : candidate;
    }

    function commitTarget(): number {
        const target = clamp(parseInt(targetText, 10));
        setTargetText(String(target));
        return target;
    }

    function step(delta: number) {
        setTargetText(String(clamp((parseInt(targetText, 10) || 1) + delta)));
        setMatched(null); setResult(null);
    }

    async function preview() {
        const target = commitTarget();
        setBusy(true); setError(null); setResult(null);
        try { setMatched((await deleteEmissionHistory(query, { page: target, page_size: pageSize, sort, order, scope, dry_run: true })).matched ?? 0); }
        catch (cause) { setError(cause instanceof Error ? cause.message : "Pratinjau gagal"); }
        finally { setBusy(false); }
    }

    async function remove() {
        const target = commitTarget();
        setBusy(true); setError(null); setResult(null);
        try {
            const count = matched ?? (await deleteEmissionHistory(query, { page: target, page_size: pageSize, sort, order, scope, dry_run: true })).matched ?? 0;
            setMatched(count);
            if (!count) return;
            if (!window.confirm(`Hapus ${fmtIntId(count)} catatan riwayat? Tindakan ini tidak dapat dibatalkan.`)) return;
            const response = await deleteEmissionHistory(query, { page: target, page_size: pageSize, sort, order, scope, dry_run: false });
            setResult(response.deleted ?? 0);
            setMatched(null);
            onDeleted();
        } catch (cause) { setError(cause instanceof Error ? cause.message : "Penghapusan gagal"); }
        finally { setBusy(false); }
    }

    return <div className="analytics-export">
        <label>Jangkauan
            <select value={scope} disabled={busy} onChange={(event) => { setScope(event.target.value as Scope); setMatched(null); setResult(null); }}>
                <option value="beyond">Hapus setelah halaman</option>
                <option value="page">Hapus hanya halaman ini</option>
            </select>
        </label>
        <span className="analytics-stepper">Halaman
            <button type="button" className="pagination-page" disabled={busy} aria-label="Kurangi nomor halaman" onClick={() => step(-1)}>−</button>
            <input type="number" min={1} max={scope === "page" ? totalPages : undefined} value={targetText} disabled={busy} aria-label="Nomor halaman"
                onChange={(event) => { setTargetText(event.target.value); setMatched(null); setResult(null); }}
                onBlur={() => commitTarget()}
                onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); commitTarget(); } }} />
            <button type="button" className="pagination-page" disabled={busy} aria-label="Tambah nomor halaman" onClick={() => step(1)}>+</button>
            <small>dari {totalPages}</small>
        </span>
        <button type="button" className="analytics-button" disabled={busy} onClick={() => void preview()}>Pratinjau</button>
        <button type="button" className="analytics-button" disabled={busy} onClick={() => void remove()}>Hapus</button>
        {matched !== null && <small>{fmtIntId(matched)} catatan cocok.</small>}
        {result !== null && <small>{fmtIntId(result)} catatan dihapus.</small>}
        {error && <span role="alert" className="analytics-error">{error}</span>}
    </div>;
}
