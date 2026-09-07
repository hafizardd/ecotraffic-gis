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
    poi: "#14b8a6",
    populationZone: "#a78bfa",
    surveyStop: "#06b6d4",
};

export const LAYER_LABELS = {
    cameras: "CCTV kamera",
    segments: "Segmen jalan",
    pois: "POI",
    populationZones: "Wilayah populasi",
    surveyStops: "Halte survei",
} as const;

export type MapLayerKey = keyof typeof LAYER_LABELS;

export const DEFAULT_VISIBLE_LAYERS: Record<MapLayerKey, boolean> = {
    cameras: true,
    segments: true,
    pois: false,
    populationZones: false,
    surveyStops: false,
};
