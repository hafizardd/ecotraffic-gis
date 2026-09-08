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
    populationZone: "#8b5cf6",
    surveyStop: "#06b6d4",
};

export const POPULATION_SCALE = [
    { color: "#ede9fe", label: "< 25.000 jiwa" },
    { color: "#c4b5fd", label: "25.000–99.999 jiwa" },
    { color: "#8b5cf6", label: "100.000–249.999 jiwa" },
    { color: "#6d28d9", label: "≥ 250.000 jiwa" },
] as const;

export const POI_CATEGORY_COLORS: Record<string, string> = {
    Kesehatan: "#ef4444",
    Kuliner: "#f97316",
    Pariwisata: "#8b5cf6",
    Pendidikan: "#3b82f6",
    Perdagangan: "#eab308",
    Peribadatan: "#ec4899",
    Perkantoran: "#84cc16",
    Transportasi: "#14b8a6",
    Pemerintahan: "#f43f5e",
};

const POI_FALLBACK_COLORS = ["#0ea5e9", "#84cc16", "#f43f5e", "#c026d3"];

export function getPoiCategoryColor(category: string): string {
    const normalizedCategory = category.trim();
    if (!normalizedCategory) return SPATIAL_COLORS.poi;
    if (POI_CATEGORY_COLORS[normalizedCategory]) return POI_CATEGORY_COLORS[normalizedCategory];

    // Keep new/unmapped categories deterministic instead of assigning a random color.
    let hash = 0;
    for (const character of normalizedCategory) hash = (hash * 31 + character.charCodeAt(0)) | 0;
    return POI_FALLBACK_COLORS[Math.abs(hash) % POI_FALLBACK_COLORS.length];
}

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
