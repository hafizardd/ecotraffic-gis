export const MISSING_LABEL = "Data tidak tersedia";

function isMissing(v: unknown): v is null | undefined {
    if (v === null || v === undefined) return true;
    return typeof v === "number" && !Number.isFinite(v);
}

// Canonical number display: Indonesian notation, at most two decimals, no
// forced trailing zeros (57 stays "57", 8.214 -> "8,21").
export function formatNumber(v: number | null | undefined, maxFractionDigits = 2): string {
    if (isMissing(v)) return MISSING_LABEL;
    return new Intl.NumberFormat("id-ID", { maximumFractionDigits: maxFractionDigits }).format(v as number);
}

// Raw backend identifiers (camera slugs, method keys) leak snake_case into the
// UI. One humanizer so every panel renders the same form.
const DISPLAY_ACRONYMS = new Set([
    "atcs", "ptz", "fm", "pku", "bpk", "smpn", "dprd", "jl", "km", "rs", "sma", "smk",
]);

export function toDisplayName(value: string | null | undefined): string {
    if (!value) return MISSING_LABEL;
    const words = value.split("_").filter(Boolean).map((token) => (
        DISPLAY_ACRONYMS.has(token.toLowerCase())
            ? token.toUpperCase()
            : token.charAt(0).toUpperCase() + token.slice(1).toLowerCase()
    ));
    return words.length > 0 ? words.join(" ") : MISSING_LABEL;
}

export const formatCameraName = toDisplayName;

// Population "method" keys from the backend are technical identifiers.
export const METHOD_LABELS: Record<string, string> = {
    segment_centroid_within: "Titik pusat segmen di dalam wilayah",
    kernel_density_estimation: "Estimasi kepadatan kernel",
    dasymetric_areal_weighting: "Pembobotan area dasimetrik",
};

export function formatMethodLabel(method: string | null | undefined): string {
    if (!method) return MISSING_LABEL;
    return METHOD_LABELS[method] ?? toDisplayName(method);
}

export function fmtIntId(v: number | null | undefined): string {
    if (isMissing(v)) return MISSING_LABEL;
    return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 }).format(v as number);
}

export function fmtFloatId(v: number | null | undefined, digits = 2): string {
    if (isMissing(v)) return MISSING_LABEL;
    return new Intl.NumberFormat("id-ID", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    }).format(v as number);
}

export function fmtEmissionId(v: number | null | undefined, unit = "g/jam"): string {
    if (isMissing(v)) return MISSING_LABEL;
    return `${fmtFloatId(v, 2)} ${unit}`;
}

export function fmtVehicleId(v: number | null | undefined): string {
    if (isMissing(v)) return MISSING_LABEL;
    return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 1 }).format(v as number);
}

export function fmtKm(v: number | null | undefined): string {
    if (isMissing(v)) return MISSING_LABEL;
    return `${fmtFloatId(v, 2)} km`;
}

export function fmtPercentId(v: number | null | undefined, digits = 1): string {
    if (isMissing(v)) return MISSING_LABEL;
    return new Intl.NumberFormat("id-ID", {
        style: "percent",
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    }).format(v as number);
}

export function fmtDateTimeId(iso: string | null | undefined): string {
    if (!iso) return MISSING_LABEL;
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return MISSING_LABEL;
    return d.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
}

// Chart ticks adapt to the selected analytical window. Time-only labels are
// useful intraday, but become ambiguous as soon as a custom range spans days.
export function fmtChartTickId(
    iso: string | null | undefined,
    from?: string | null,
    to?: string | null,
): string {
    if (!iso) return MISSING_LABEL;
    const value = new Date(iso);
    if (Number.isNaN(value.getTime())) return MISSING_LABEL;
    const start = from ? Date.parse(from) : Number.NaN;
    const end = to ? Date.parse(to) : Number.NaN;
    const duration = Number.isFinite(start) && Number.isFinite(end) ? Math.abs(end - start) : 0;
    const options: Intl.DateTimeFormatOptions = duration > 7 * 86400000
        ? { day: "2-digit", month: "short" }
        : duration > 24 * 3600000
            ? { day: "2-digit", month: "short", hour: "2-digit" }
            : { hour: "2-digit", minute: "2-digit" };
    return value.toLocaleString("id-ID", options).replace(".", ":");
}
