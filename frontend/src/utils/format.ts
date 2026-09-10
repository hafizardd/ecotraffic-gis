export const MISSING_LABEL = "Data tidak tersedia";

function isMissing(v: unknown): v is null | undefined {
    if (v === null || v === undefined) return true;
    return typeof v === "number" && !Number.isFinite(v);
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
