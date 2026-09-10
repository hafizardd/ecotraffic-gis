"use client";
import { useCallback, useState } from "react";
import { useEmissionAnalytics } from "@/context/EmissionAnalyticsContext";
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import { fetchEmissionHistory } from "@/services/api";
import useAnalyticsResource from "@/hooks/useAnalyticsResource";
import { fmtDateTimeId, fmtFloatId } from "@/utils/format";
import type { VehicleRates } from "@/types";
import EmissionExport from "./EmissionExport";

function categoryRates(value: VehicleRates | null) {
    return value ? Object.entries(value).map(([category, rate]) => <div key={category}>{category}: {fmtFloatId(rate, 2)}</div>) : "—";
}

export default function EmissionHistory() {
    const { query } = useEmissionAnalytics();
    const queryKey = JSON.stringify(query);
    const [paging, setPaging] = useState({ key: "", page: 1 });
    const page = paging.key === queryKey ? paging.page : 1;
    const load = useCallback((signal: AbortSignal) => fetchEmissionHistory(query, page, signal), [query, page]);
    const { data, loading, error } = useAnalyticsResource(`${queryKey}:${page}`, load);
    return <section className="page-card" aria-label="Riwayat emisi segmen" aria-busy={loading}>
        <div className="card-header"><strong>Riwayat perhitungan segmen</strong><span>{data?.total ?? 0} catatan</span></div>
        <EmissionExport />
        <p className="analytics-note">Laju polutan: kg/hour · Volume: vehicles/hour · VKT: km/hour. Sumber LIVE berarti hasil pengamatan langsung yang telah disimpan. Data sintetis dan replay dikecualikan.</p>
        {loading ? <div className="unavailable-state">Memuat riwayat…</div> : error ? <p role="alert" className="analytics-error">{error}</p> : !data?.data.length ?
            <div className="unavailable-state">Tidak ada pengamatan segmen pada rentang dan lokasi ini.</div> :
            <div className="table-wrap analytics-history-scroll"><table className="priority-table analytics-history-table"><thead><tr>
                <th>Periode</th><th>Segmen / koridor</th>{EMISSION_DEFINITIONS.map((p) => <th key={p.key}>{p.label}<br />kg/hour</th>)}
                <th>Volume<br />vehicles/hour</th><th>VKT<br />km/hour</th><th>Sumber / metode</th><th>Observed at</th><th>Processed at</th><th>Versi / audit</th>
            </tr></thead><tbody>{data.data.map((row) => <tr key={row.id}>
                <td>{fmtDateTimeId(row.period_start)}<br /><small>s/d {fmtDateTimeId(row.period_end)}</small></td>
                <td><strong>{row.segment_name}</strong><br />{row.segment_id}<br /><small>{row.corridor_name}</small></td>
                {EMISSION_DEFINITIONS.map((p) => <td key={p.key}>{row.emissions_kg_h[p.key] == null ? "—" : fmtFloatId(row.emissions_kg_h[p.key]!, 6)}</td>)}
                <td>{categoryRates(row.volume_per_hour)}</td><td>{categoryRates(row.vkt_km_h)}</td>
                <td><b>{row.source_mode}</b><br />{row.quality_status}<br /><small>{row.vehicle_count_semantics}<br />{row.calculation_mode}</small></td>
                <td>{fmtDateTimeId(row.observed_at)}</td><td>{fmtDateTimeId(row.processed_at)}</td>
                <td>v{row.calculation_version}<details><summary>Jejak sumber</summary><p>{row.source_cameras.join(", ") || "Tidak tercatat"}</p><p>Stream: {row.source_streams.join(", ")}</p><p>{row.source_observation_count} observasi · {fmtFloatId(row.observation_duration_seconds, 2)} detik</p><pre>{JSON.stringify(row.calculation_metadata, null, 2)}</pre></details></td>
            </tr>)}</tbody></table></div>}
        <div className="analytics-pagination"><button className="analytics-button" disabled={loading || page <= 1} onClick={() => setPaging({ key: queryKey, page: page - 1 })}>Sebelumnya</button>
            <span>Halaman {page} / {Math.max(1, Math.ceil((data?.total ?? 0) / 25))}</span>
            <button className="analytics-button" disabled={loading || !data || page * 25 >= data.total} onClick={() => setPaging({ key: queryKey, page: page + 1 })}>Berikutnya</button>
        </div>
    </section>;
}
