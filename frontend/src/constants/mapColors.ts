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
    surveyStop: "#06b6d4",
};

export const FIVE_TIER_COLORS = {
    veryLow: "#bbf7d0",
    low: "#22c55e",
    medium: "#facc15",
    high: "#f97316",
    veryHigh: "#ef4444",
    unknown: "#94a3b8",
} as const;

export const FIVE_TIER_LEGEND = [
    { color: FIVE_TIER_COLORS.veryHigh, label: "Sangat Tinggi" },
    { color: FIVE_TIER_COLORS.high, label: "Tinggi" },
    { color: FIVE_TIER_COLORS.medium, label: "Sedang" },
    { color: FIVE_TIER_COLORS.low, label: "Rendah" },
    { color: FIVE_TIER_COLORS.veryLow, label: "Sangat Rendah" },
] as const;

// Maps both the GeoJSON labels and the Excel "Hijau Muda (Sangat Rendah)"
// forms onto one palette. Check the "sangat" variants first.
export function classificationTier(value: string | null | undefined): 1 | 2 | 3 | 4 | 5 | 0 {
    const v = (value ?? "").toLowerCase();
    if (!v) return 0;
    if (v.includes("sangat tinggi") || v.includes("merah")) return 5;
    if (v.includes("sangat rendah") || v.includes("hijau muda")) return 1;
    if (v.includes("tinggi") || v.includes("oranye") || v.includes("orange")) return 4;
    if (v.includes("sedang") || v.includes("kuning")) return 3;
    if (v.includes("rendah") || v.includes("hijau")) return 2;
    return 0;
}

export function classificationColor(value: string | null | undefined): string {
    const tier = classificationTier(value);
    return [FIVE_TIER_COLORS.unknown, FIVE_TIER_COLORS.veryLow, FIVE_TIER_COLORS.low, FIVE_TIER_COLORS.medium, FIVE_TIER_COLORS.high, FIVE_TIER_COLORS.veryHigh][tier];
}

export const LAYER_LABELS = {
    cameras: "CCTV kamera",
    segments: "Segmen jalan",
    surveyStops: "Halte survei",
    activityGrid: "Potensi aktivitas (grid)",
} as const;

export type MapLayerKey = keyof typeof LAYER_LABELS;

export const DEFAULT_VISIBLE_LAYERS: Record<MapLayerKey, boolean> = {
    cameras: true,
    segments: true,
    surveyStops: false,
    activityGrid: false,
};
