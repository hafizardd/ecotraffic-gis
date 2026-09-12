"use client"

import { useEmissionsContext } from "@/context/EmissionsContext"
import { EMISSION_DEFINITIONS } from "@/constants/emissions";
import Skeleton from "@/components/ui/Skeleton";
import { formatNumber } from "@/utils/format";
import { POLLUTANT_TEXT_CLASS } from "@/styles/tailwind";

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
    return (
        <section className="flex min-w-0 items-stretch border-b border-[var(--border)] bg-[#071422] py-[9px] pr-[14px] pl-[18px] max-[760px]:overflow-x-auto max-[760px]:p-[7px_9px]" aria-label="Ringkasan emisi global">
            <div className="flex w-[150px] flex-col justify-center border-r border-[var(--border)] max-[1100px]:w-[125px] max-[760px]:hidden"><span className="text-[8px] font-extrabold tracking-[0.15em] text-[var(--green)]">GLOBAL</span><strong className="mt-[3px] text-[11px] font-semibold">Emisi Saat Ini</strong></div>
            <div className="grid min-w-0 flex-1 grid-cols-[repeat(8,minmax(106px,1fr))] max-[760px]:h-12 max-[760px]:min-w-[848px]">
                {hasData ? (
                    EMISSION_DEFINITIONS.map(({ key, label }) => (
                        <div key={key} className={`grid grid-cols-1 grid-rows-[auto_auto_auto] content-center gap-y-px border-r border-[var(--border)] px-[10px] last:border-0 max-[1100px]:px-2 max-[760px]:px-3 ${POLLUTANT_TEXT_CLASS[key]}`}>
                            <span className="flex min-w-0 items-center gap-1.5 text-[10px] font-extrabold"><span className="h-[7px] w-[7px] flex-[0_0_7px] rounded-full bg-current" />{label}</span>
                            <span className="flex min-w-0 items-center gap-1.5"><strong className="text-base text-[var(--text)] tabular-nums">{formatNumber(totals[key])}</strong><span className="text-[8px] text-[var(--secondary)]">g/min</span></span>
                            <span className="ml-auto text-[8px] text-[var(--muted)]">{formatNumber(totalsKgHr[key])} kg/hr</span>
                        </div>
                    ))
                ) : (
                    EMISSION_DEFINITIONS.map(({ key }) => (
                        <div key={key} className="grid grid-cols-1 grid-rows-[auto_auto_auto] content-center gap-y-px border-r border-[var(--border)] px-[10px] last:border-0 max-[1100px]:px-2 max-[760px]:px-3">
                            <span className="flex min-w-0 items-center gap-1.5 text-[10px] font-extrabold"><Skeleton height={10} width="68%" /></span>
                            <span className="flex min-w-0 items-center gap-1.5"><Skeleton height={16} width="82%" /></span>
                            <span className="ml-auto text-[8px] text-[var(--muted)]"><Skeleton height={8} width="56%" /></span>
                        </div>
                    ))
                )}
            </div>
        </section>
    );
}
