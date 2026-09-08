export const SEGMENT_COLORS = {
    noData: "#64748b",
    low: "#22c55e",
    medium: "#facc15",
    high: "#f97316",
    critical: "#ef4444",
};

export const CAMERA_TIER_COLORS = {
    unavailable: "#94a3b8",
    low: "#22c55e",
    medium: "#f59e0b",
    high: "#ef4444",
};

export const FRESHNESS_COLORS = {
    fresh: "#22c55e",
    aging: "#f59e0b",
    stale: "#f05252",
    unknown: "#94a3b8",
};

export const SPATIAL_COLORS = {
    populationZone: "#8b5cf6",
    surveyStop: "#06b6d4",
};

export const POPULATION_SCALE = [
    { color: "#ede9fe", label: "< 25.000 jiwa" },
    { color: "#c4b5fd", label: "25.000–99.999 jiwa" },
    { color: "#8b5cf6", label: "100.000–249.999 jiwa" },
    { color: "#6d28d9", label: "≥ 250.000 jiwa" },
] as const;

export const LAYER_LABELS = {
    cameras: "CCTV kamera",
    segments: "Segmen jalan",
    populationZones: "Wilayah populasi",
    surveyStops: "Halte survei",
} as const;

export type MapLayerKey = keyof typeof LAYER_LABELS;

export const DEFAULT_VISIBLE_LAYERS: Record<MapLayerKey, boolean> = {
    cameras: true,
    segments: true,
    populationZones: false,
    surveyStops: false,
};
