"use client";

import { Car, Bike, Bus, Truck } from "lucide-react";
import { EmissionUpdate } from "@/types";
import Skeleton from "@/components/ui/Skeleton";
import { formatNumber } from "@/utils/format";

interface VehicleCountProps {
    emission: EmissionUpdate | null;
}

export default function VehicleCount({ emission }: VehicleCountProps) {
    if (!emission) {
        return <div className="vehicle-grid">{[0, 1, 2, 3].map((key) => (
            <div key={key} className="vehicle-card"><Skeleton height={34} width={34} radius={7} /><Skeleton height={16} width="60%" /></div>
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
        <p className="text-caption">{isInstant ? "Kendaraan pada frame terbaru." : "Kendaraan terlihat atau rata-rata snapshot. Ini bukan volume lalu lintas per jam."}</p>
        <div className="vehicle-grid">
            {vehicles.map(({ label, count, Icon }) => (
                <div
                    key={label}
                    className="vehicle-card"
                >
                    <div className="vehicle-icon">
                        <Icon aria-hidden="true" />
                    </div>
                    <div className="vehicle-copy">
                        <span>{label}</span><strong>{isInstant ? Math.round(count) : formatNumber(count)}</strong>
                    </div>
                </div>
            ))}
        </div>
        </>
    );
}
