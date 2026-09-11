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

export const FIVE_TIER_COLORS = {
    veryLow: "#bbf7d0",
    low: "#22c55e",
    medium: "#facc15",
    high: "#f97316",
    veryHigh: "#ef4444",
    unknown: "#94a3b8",
} as const;

// Fixed AHP-score ramp (score is 1..100), kept as the fallback for the grid
// fill when the viewport has no quantile spread. The live ramp itself is
// rebuilt per viewport from `breaksToStops`.
export const ACTIVITY_SCORE_RAMP: ReadonlyArray<[number, string]> = [
    [1, FIVE_TIER_COLORS.veryLow],
    [25, FIVE_TIER_COLORS.low],
    [50, FIVE_TIER_COLORS.medium],
    [75, FIVE_TIER_COLORS.high],
    [100, FIVE_TIER_COLORS.veryHigh],
];

// MapLibre interpolate stops, flat: [stop, color, stop, color, ...].
export const ACTIVITY_SCORE_STOPS: ReadonlyArray<number | string> = ACTIVITY_SCORE_RAMP.flat();

// Viewport quantile breaks (min..max, one per tier colour) -> flat MapLibre
// `interpolate` stops. Returns null for a degenerate viewport (too few points
// or no spread) so the caller can fall back to the discrete tier `step`.
export function breaksToStops(breaks: number[] | null | undefined): (number | string)[] | null {
    if (!breaks || breaks.length < 2) return null;
    const colors = [FIVE_TIER_COLORS.veryLow, FIVE_TIER_COLORS.low, FIVE_TIER_COLORS.medium, FIVE_TIER_COLORS.high, FIVE_TIER_COLORS.veryHigh];
    return breaks.flatMap((value, index) => [value, colors[Math.min(index, colors.length - 1)]]);
}

// Human-readable quantile boundaries for the legend.
export function breaksToLabels(breaks: number[] | null | undefined): string[] | null {
    if (!breaks || breaks.length < 2) return null;
    return breaks.map((value) => (Math.abs(value) >= 10 ? value.toFixed(0) : value.toFixed(1)));
}

export function activityGradientCss(): string {
    return `linear-gradient(90deg, ${ACTIVITY_SCORE_RAMP.map(([score, color]) => `${color} ${score}%`).join(", ")})`;
}

// Bus-stop intervention ramp, deliberately inverted from the activity ramp:
// a LOW score means poor condition, so it is red and is the top intervention
// priority; a HIGH score is green (healthy). Score is 0..100.
export const BUS_STOP_INTERVENTION_RAMP: ReadonlyArray<[number, string]> = [
    [0, "#ef4444"],
    [50, "#facc15"],
    [100, "#22c55e"],
];

function hexToRgb(hex: string): [number, number, number] {
    const value = parseInt(hex.slice(1), 16);
    return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function mixHex(a: string, b: string, t: number): string {
    const [r1, g1, b1] = hexToRgb(a);
    const [r2, g2, b2] = hexToRgb(b);
    const byte = (x: number, y: number) => Math.round(x + (y - x) * t).toString(16).padStart(2, "0");
    return `#${byte(r1, r2)}${byte(g1, g2)}${byte(b1, b2)}`;
}

export function interventionColor(score: number | null | undefined): string {
    if (score == null || !Number.isFinite(Number(score))) return FIVE_TIER_COLORS.unknown;
    const value = Math.max(0, Math.min(100, Number(score)));
    for (let i = 1; i < BUS_STOP_INTERVENTION_RAMP.length; i += 1) {
        const [low, lowColor] = BUS_STOP_INTERVENTION_RAMP[i - 1];
        const [high, highColor] = BUS_STOP_INTERVENTION_RAMP[i];
        if (value <= high) return mixHex(lowColor, highColor, (value - low) / (high - low));
    }
    return BUS_STOP_INTERVENTION_RAMP[BUS_STOP_INTERVENTION_RAMP.length - 1][1];
}

export function interventionGradientCss(): string {
    return `linear-gradient(90deg, ${BUS_STOP_INTERVENTION_RAMP.map(([score, color]) => `${color} ${score}%`).join(", ")})`;
}

// Icon colour that stays legible on the ramp's red/yellow/green background.
export function readableTextOn(color: string): string {
    const [r, g, b] = hexToRgb(color);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.6 ? "#0f172a" : "#ffffff";
}

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

// Two exclusive thematic views: the segmented control picks one and the other
// view's layers (and legend sections) disappear. Bus stops and the activity
// hexagon grid are combined into one "Halte & Potensi" view. The basemap/style
// stay global.
export type MapMode = "traffic" | "potential";

export const MAP_MODES: { key: MapMode; label: string }[] = [
    { key: "traffic", label: "CCTV & Segmen" },
    { key: "potential", label: "Halte & Potensi" },
];

export const MODE_VISIBILITY: Record<MapMode, Record<MapLayerKey, boolean>> = {
    traffic: { cameras: true, segments: true, surveyStops: false, activityGrid: false },
    potential: { cameras: false, segments: false, surveyStops: true, activityGrid: true },
};

export const DEFAULT_MAP_MODE: MapMode = "traffic";

export function isMapMode(value: unknown): value is MapMode {
    return value === "traffic" || value === "potential";
}

// Bus-stop accessibility buffer, matches backend K4_BUFFER_M.
export const BUS_STOP_BUFFER_M = 500;
