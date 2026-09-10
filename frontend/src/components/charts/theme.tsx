"use client";

import { useEffect, useState } from "react";

// One interaction language for every chart: tooltip chrome, axes, grid and a
// first-mount-only entrance animation that periodic refetches never replay.
export const CHART_TOOLTIP_STYLE = {
    backgroundColor: "#0e1d2e",
    border: "1px solid #334155",
    borderRadius: 8,
    boxShadow: "0 14px 34px rgba(0, 0, 0, 0.4)",
    color: "#f8fafc",
    fontSize: 12,
} as const;

export const CHART_TOOLTIP_LABEL_STYLE = { color: "#94a3b8", marginBottom: 6 } as const;
export const CHART_AXIS = { stroke: "#94a3b8", tick: { fill: "#94a3b8", fontSize: 11 }, tickLine: false } as const;
export const CHART_GRID_STROKE = "#24364a";

export function entranceProps(active: boolean, index = 0) {
    return {
        isAnimationActive: active,
        animationDuration: 650,
        animationEasing: "ease-out" as const,
        animationBegin: active ? index * 90 : 0,
    };
}

export function useChartEntrance(hasData: boolean) {
    const [animated, setAnimated] = useState(false);
    const [reduced, setReduced] = useState(false);
    useEffect(() => {
        const query = window.matchMedia("(prefers-reduced-motion: reduce)");
        const update = () => setReduced(query.matches);
        update();
        query.addEventListener("change", update);
        return () => query.removeEventListener("change", update);
    }, []);
    useEffect(() => {
        if (!hasData) return;
        // Hold the entrance flag for one animation window, then never replay it
        // on periodic refetches.
        const timer = setTimeout(() => setAnimated(true), 800);
        return () => clearTimeout(timer);
    }, [hasData]);
    return { active: hasData && !reduced && !animated, reduced };
}
