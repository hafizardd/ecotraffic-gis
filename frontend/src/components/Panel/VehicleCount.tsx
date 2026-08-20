"use client";

import { EmissionUpdate } from "@/types";

interface VehicleCountProps {
    emission: EmissionUpdate | null;
}

function CarIcon() {
    return (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M5 17h14M5 17a2 2 0 01-2-2v-3l2-5h14l2 5v3a2 2 0 01-2 2M5 17a2 2 0 002 2h1a2 2 0 002-2M14 17a2 2 0 002 2h1a2 2 0 002-2" />
            <circle cx="7.5" cy="17" r="1.5" />
            <circle cx="16.5" cy="17" r="1.5" />
        </svg>
    );
}

function MotorcycleIcon() {
    return (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="5" cy="17" r="3" />
            <circle cx="19" cy="17" r="3" />
            <path d="M5 17l4-8h4l3 5h3" />
            <path d="M13 9l2-4h3" />
        </svg>
    );
}

function BusIcon() {
    return (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="4" y="3" width="16" height="16" rx="2" />
            <path d="M4 11h16M4 19l2-2h12l2 2" />
            <circle cx="8" cy="19" r="1.5" />
            <circle cx="16" cy="19" r="1.5" />
        </svg>
    );
}

function TruckIcon() {
    return (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M1 3h15v13H1zM16 8h4l3 4v4h-7V8z" />
            <circle cx="5.5" cy="18.5" r="2.5" />
            <circle cx="18.5" cy="18.5" r="2.5" />
        </svg>
    );
}

export default function VehicleCount({ emission }: VehicleCountProps) {
    if (!emission) {
        return <div className="data-empty"><span className="loading-spinner small" />Menunggu data kendaraan...</div>;
    }

    const vehicles = [
        { label: "Car", count: emission.car, Icon: CarIcon },
        { label: "Motorcycle", count: emission.motorcycle, Icon: MotorcycleIcon },
        { label: "Bus", count: emission.bus, Icon: BusIcon },
        { label: "Truck", count: emission.truck, Icon: TruckIcon },
    ];
    
    return (
        <div className="vehicle-grid">
            {vehicles.map(({ label, count, Icon }) => (
                <div
                    key={label}
                    className="vehicle-card"
                >
                    <div className="vehicle-icon">
                        <Icon />
                    </div>
                    <div className="vehicle-copy">
                        <span>{label}</span><strong>{count}</strong>
                    </div>
                </div>
            ))}
        </div>
    );
}
