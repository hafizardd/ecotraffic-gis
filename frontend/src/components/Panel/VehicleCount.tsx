"use client";

import { Car, Bike, Bus, Truck } from "lucide-react";
import { EmissionUpdate } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import { formatNumber } from "@/utils/format";
import { STAT_GRID_CLASS, TEXT_CAPTION_CLASS } from "@/styles/tailwind";

const VEHICLE_CARD_CLASS = "flex min-h-[58px] items-center gap-[11px] rounded-lg border border-[var(--border)] bg-[var(--card-2)] px-[11px] py-[9px]";

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
        { label: "Car", count: counts.car ?? 0, Icon: Car },
        { label: "Motorcycle", count: counts.motorcycle ?? 0, Icon: Bike },
        { label: "Bus", count: counts.bus ?? 0, Icon: Bus },
        { label: "Truck", count: counts.truck ?? 0, Icon: Truck },
    ];
    
    return (
        <>
        <p className={TEXT_CAPTION_CLASS}>{isInstant ? "Kendaraan pada frame terbaru." : "Kendaraan terlihat atau rata-rata snapshot. Ini bukan volume lalu lintas per jam."}</p>
        <div className={STAT_GRID_CLASS}>
            {vehicles.map(({ label, count, Icon }) => (
                <div
                    key={label}
                    className={VEHICLE_CARD_CLASS}
                >
                    <div className="grid h-[34px] w-[34px] place-items-center rounded-[7px] bg-[#13263b] text-[#8ba0b8] [&>svg]:h-[19px] [&>svg]:w-[19px]">
                        <Icon aria-hidden="true" />
                    </div>
                    <div className="flex flex-1 items-center justify-between gap-[5px] [&>span]:text-[9px] [&>span]:text-[var(--secondary)] [&>strong]:text-[17px] [&>strong]:tabular-nums">
                        <span>{label}</span><strong>{isInstant ? Math.round(count) : formatNumber(count)}</strong>
                    </div>
                </div>
            ))}
        </div>
        </>
    );
}
