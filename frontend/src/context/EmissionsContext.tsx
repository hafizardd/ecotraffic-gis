"use client";

import { createContext, useContext, ReactNode } from "react";
import useEmissions from "@/hooks/useEmissions";
import { EmissionUpdate, RealtimeSegmentEmission, SegmentUpdate } from "@/types";

interface EmissionsContextValue { emissionMap: Map<string, EmissionUpdate>; segmentMap: Map<string, SegmentUpdate["data"]>; segmentEmissionMap: Map<string, RealtimeSegmentEmission>; connectionStatus: "connecting" | "connected" | "disconnected"; lastMessageAt: string | null; error: string | null; }
const EmissionsContext = createContext<EmissionsContextValue>({ emissionMap: new Map(), segmentMap: new Map(), segmentEmissionMap: new Map(), connectionStatus: "connecting", lastMessageAt: null, error: null });

export function EmissionsProvider({ children }: { children: ReactNode }) {
    const value = useEmissions();
    return (
            <EmissionsContext.Provider value={value}>
            {children}
        </EmissionsContext.Provider>
    );
}

export function useEmissionsContext() {
    const context = useContext(EmissionsContext);
    if (!context) {
        throw new Error("useEmissionsContext must be used within EmissionsProvider");
    }
    return context;
}
