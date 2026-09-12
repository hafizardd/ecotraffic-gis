"use client";

import { useEffect, useState } from "react";

// One interaction language for every chart: tooltip chrome, axes, grid and a
// first-mount-only entrance animation that periodic refetches never replay.
export const CHART_TOOLTIP_STYLE = {
    backgroundColor: "var(--surface-sunken)",
    border: "1px solid var(--contour-strong)",
    borderRadius: 6,
    boxShadow: "0 14px 34px rgba(0, 0, 0, 0.4)",
    color: "var(--text)",
    fontFamily: "var(--font-data)",
    fontSize: 11,
    lineHeight: 1.45,
    padding: "9px 11px",
} as const;

export const CHART_TOOLTIP_LABEL_STYLE = { color: "var(--secondary)", marginBottom: 6, fontWeight: 600 } as const;
export const CHART_AXIS = {
    stroke: "var(--contour-strong)",
    tick: { fill: "var(--muted)", fontFamily: "var(--font-data)", fontSize: 10 },
    tickLine: false,
} as const;
export const CHART_GRID_STROKE = "var(--contour)";
export const CHART_TOOLTIP_CURSOR = { stroke: "var(--selection)", strokeWidth: 1, strokeDasharray: "3 4", opacity: 0.58 } as const;

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
