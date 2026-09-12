"use client";

import { Car, Bike, Bus, Truck } from "lucide-react";
import { EmissionUpdate } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import { formatNumber } from "@/utils/format";
import { STAT_GRID_CLASS, TEXT_CAPTION_CLASS } from "@/styles/tailwind";

const VEHICLE_CARD_CLASS = "flex min-h-[62px] items-center gap-3 rounded-sm border border-(--border) bg-(--surface-raised) px-3 py-2.5";

interface VehicleCountProps {
    emission: EmissionUpdate | null;
}

export default function VehicleCount({ emission }: VehicleCountProps) {
    if (!emission) {
        return <div className={STAT_GRID_CLASS}>{[0, 1, 2, 3].map((key) => (
            <div key={key} className={VEHICLE_CARD_CLASS}><Skeleton height={34} width={34} radius={7} /><Skeleton height={16} width="60%" /></div>
        ))}</div>;
    }

    const counts = emission.source === "tracking" && emission.occupancy
        ? emission.occupancy
        : emission;
    const isInstant = emission.source === "tracking" && !!emission.occupancy;
    const vehicles = [
        { label: "Mobil", count: counts.car ?? 0, Icon: Car },
        { label: "Motor", count: counts.motorcycle ?? 0, Icon: Bike },
        { label: "Bus", count: counts.bus ?? 0, Icon: Bus },
        { label: "Truk", count: counts.truck ?? 0, Icon: Truck },
    ];
    
    return (
        <>
        <p className={TEXT_CAPTION_CLASS}>{isInstant ? "Kendaraan pada frame terbaru." : "Kendaraan terlihat atau rata-rata pemantauan berkala. Ini bukan volume lalu lintas per jam."}</p>
        <div className={STAT_GRID_CLASS}>
            {vehicles.map(({ label, count, Icon }) => (
                <div
                    key={label}
                    className={VEHICLE_CARD_CLASS}
                >
                    <div className="grid h-9 w-9 place-items-center rounded-sm bg-(--canvas) text-(--muted) [&>svg]:h-[18px] [&>svg]:w-[18px]">
                        <Icon aria-hidden="true" />
                    </div>
                    <div className="flex min-w-0 flex-1 items-baseline justify-between gap-2 [&>span]:text-[10px] [&>span]:text-(--secondary) [&>strong]:font-(family-name:--font-data) [&>strong]:text-[18px] [&>strong]:font-semibold [&>strong]:text-(--text) [&>strong]:tabular-nums">
                        <span>{label}</span><strong>{isInstant ? Math.round(count) : formatNumber(count)}</strong>
                    </div>
                </div>
            ))}
        </div>
        </>
    );
}
