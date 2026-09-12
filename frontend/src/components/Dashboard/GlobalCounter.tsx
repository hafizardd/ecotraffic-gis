"use client"

import { useEmissionsContext } from "@/context/EmissionsContext"
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import Skeleton from "@/components/ui/Skeleton";
import { formatNumber } from "@/utils/format";
import { POLLUTANT_TEXT_CLASS } from "@/styles/tailwind";
import { ChevronDown } from "lucide-react";

export default function GlobalCounter() {
    const { emissionMap } = useEmissionsContext();

    const totals = Object.fromEntries(EMISSION_DEFINITIONS.map(({ key }) => [key, 0])) as Record<string, number>;
    const totalsKgHr = Object.fromEntries(EMISSION_DEFINITIONS.map(({ key }) => [key, 0])) as Record<string, number>;

    for (const update of emissionMap.values()) {
        for (const { key, field, hourlyField } of EMISSION_DEFINITIONS) {
            totals[key] += Number(update[field] ?? 0);
            totalsKgHr[key] += Number(update[hourlyField] ?? 0);
        }
    }

    const hasData = emissionMap.size > 0;
    const co2Total = totals.co2;

    const metrics = EMISSION_DEFINITIONS.map(({ key, label }) => (
        <div key={key} className={`grid min-w-23 grid-rows-[auto_auto_auto] content-center gap-y-0.5 border-r border-(--border) px-3 last:border-0 ${POLLUTANT_TEXT_CLASS[key]}`}>
            {hasData ? <>
                <dt className="flex min-w-0 items-center gap-1.5 text-[10px] font-bold tracking-[0.04em] uppercase"><span className="h-1.5 w-1.5 flex-[0_0_6px] rounded-full bg-current" aria-hidden="true" />{label}</dt>
                <dd className="m-0 flex min-w-0 items-baseline gap-1.5 text-(--text)"><strong className="font-(family-name:--font-data) text-[15px] leading-5 font-semibold tabular-nums">{formatNumber(totals[key])}</strong><span className="text-[10px] text-(--secondary)">g/min</span></dd>
                <dd className="m-0 font-(family-name:--font-data) text-[10px] leading-3 text-(--muted) tabular-nums">{formatNumber(totalsKgHr[key])} kg/jam</dd>
            </> : <>
                <dt><Skeleton height={10} width="62%" /></dt>
                <dd className="m-0"><Skeleton height={18} width="82%" /></dd>
                <dd className="m-0"><Skeleton height={8} width="54%" /></dd>
            </>}
        </div>
    ));

    return (
        <>
            <section className="flex min-h-15 min-w-0 items-stretch border-b border-(--border) bg-(--surface-sunken) py-2 pr-3 pl-4 max-[760px]:hidden" aria-label="Ringkasan emisi kota">
                <div className="flex w-35.5 flex-[0_0_142px] flex-col justify-center border-r border-(--border) max-[1100px]:w-31 max-[1100px]:basis-31"><span className="text-[10px] font-bold tracking-[0.14em] text-(--brand-strong) uppercase">Telemetri kota</span><strong className="mt-0.5 text-[12px] font-semibold">8 polutan · saat ini</strong></div>
                <dl className="grid min-w-0 flex-1 grid-cols-[repeat(8,minmax(92px,1fr))]">{metrics}</dl>
            </section>
            <details className="group hidden min-w-0 max-w-full overflow-hidden border-b border-(--border) bg-(--surface-sunken) max-[760px]:block">
                <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 px-3 marker:content-none [&::-webkit-details-marker]:hidden">
                    <span className="text-[10px] font-bold tracking-[0.12em] text-(--brand-strong) uppercase">Telemetri</span>
                    <span className="h-3 border-l border-(--border)" aria-hidden="true" />
                    <span className="text-[12px] text-(--secondary)">CO₂</span>
                    <strong className="font-(family-name:--font-data) text-[13px] font-semibold tabular-nums">{hasData ? `${formatNumber(co2Total)} g/min` : "Memuat data"}</strong>
                    <span className="ml-auto text-[10px] text-(--muted)">Lihat 8 polutan</span>
                    <ChevronDown className="h-4 w-4 text-(--secondary) transition-transform duration-200 group-open:rotate-180" aria-hidden="true" />
                </summary>
                <div className="overflow-x-auto border-t border-(--border)">
                    <dl className="grid min-w-224 grid-cols-[repeat(8,minmax(112px,1fr))] py-2">{metrics}</dl>
                </div>
            </details>
        </>
    );
}
