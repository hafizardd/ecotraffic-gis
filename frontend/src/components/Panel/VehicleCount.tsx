"use client";

import { Car, Bike, Bus, Truck } from "lucide-react";
import { EmissionUpdate } from "@/types";

interface VehicleCountProps {
    emission: EmissionUpdate | null;
}

export default function VehicleCount({ emission }: VehicleCountProps) {
    if (!emission) {
        return <div className="data-empty"><span className="loading-spinner small" />Menunggu data kendaraan...</div>;
    }

    const vehicles = [
        { label: "Car", count: emission.car ?? 0, Icon: Car },
        { label: "Motorcycle", count: emission.motorcycle ?? 0, Icon: Bike },
        { label: "Bus", count: emission.bus ?? 0, Icon: Bus },
        { label: "Truck", count: emission.truck ?? 0, Icon: Truck },
    ];
    
    return (
        <>
        <p className="text-xs text-zinc-500">Kendaraan terlihat pada frame terbaru atau rata-rata snapshot. Ini bukan volume lalu lintas per jam.</p>
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
                        <span>{label}</span><strong>{Number.isInteger(count) ? count : count.toFixed(1)}</strong>
                    </div>
                </div>
            ))}
        </div>
        </>
    );
}
