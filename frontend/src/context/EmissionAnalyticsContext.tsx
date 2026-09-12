"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { AnalyticsQuery, AnalyticsSegmentOption, EmissionAnalyticsFilter } from "@/types";
import { fetchAnalyticsOptions } from "@/services/api";
import { analyticsQuery } from "@/utils/emissionAnalytics";

interface AnalyticsContextValue {
    filter: EmissionAnalyticsFilter; query: AnalyticsQuery; options: AnalyticsSegmentOption[];
    optionsError: string | null; setFilter: (patch: Partial<EmissionAnalyticsFilter>) => void; refresh: () => void;
}
const AnalyticsContext = createContext<AnalyticsContextValue | null>(null);

export function EmissionAnalyticsProvider({ children }: { children: ReactNode }) {
    const [filter, updateFilter] = useState<EmissionAnalyticsFilter>({ timeRange: "24h", segmentId: null, corridorId: null, from: null, to: null });
    const [anchor, setAnchor] = useState(() => new Date().toISOString());
    const [options, setOptions] = useState<AnalyticsSegmentOption[]>([]);
    const [optionsError, setOptionsError] = useState<string | null>(null);
    const [refreshVersion, setRefreshVersion] = useState(0);
    const refresh = useCallback(() => { setAnchor(new Date().toISOString()); setRefreshVersion((v) => v + 1); }, []);
    const setFilter = useCallback((patch: Partial<EmissionAnalyticsFilter>) => {
        updateFilter((previous) => ({ ...previous, ...patch }));
        setAnchor(new Date().toISOString());
    }, []);
    useEffect(() => {
        const controller = new AbortController();
        fetchAnalyticsOptions(controller.signal).then((value) => { setOptions(value.segments); setOptionsError(null); }).catch((error: Error) => {
            if (!controller.signal.aborted) setOptionsError(error.message);
        });
        return () => controller.abort();
    }, [refreshVersion]);
    useEffect(() => {
        if (filter.from || filter.to) return;
        const timer = setInterval(refresh, 60000);
        return () => clearInterval(timer);
    }, [filter.from, filter.to, refresh]);
    const query = useMemo(() => analyticsQuery(filter, anchor), [filter, anchor]);
    return <AnalyticsContext.Provider value={{ filter, query, options, optionsError, setFilter, refresh }}>{children}</AnalyticsContext.Provider>;
}

export function useEmissionAnalytics() {
    const context = useContext(AnalyticsContext);
    if (!context) throw new Error("EmissionAnalyticsProvider is required");
    return context;
}
