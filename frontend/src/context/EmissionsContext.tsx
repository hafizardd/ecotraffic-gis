"use client";

import { createContext, useContext, ReactNode } from "react";
import useEmissions from "@/hooks/useEmissions";
import { EmissionUpdate } from "@/types";

const EmissionsContext = createContext<Map<string, EmissionUpdate>>(new Map());

export function EmissionsProvider({ children }: { children: ReactNode }) {
    const emissionMap = useEmissions();
    return (
        <EmissionsContext.Provider value={emissionMap}>
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