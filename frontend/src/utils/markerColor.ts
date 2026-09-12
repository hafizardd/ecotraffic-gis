export type CameraTier = "unavailable" | "low" | "medium" | "high";

export function getCameraTier(co2_g_per_min: number | null | undefined): CameraTier {
    if (co2_g_per_min == null || Number.isNaN(co2_g_per_min)) return "unavailable";
    if (co2_g_per_min < 500) return "low";
    if (co2_g_per_min <= 1500) return "medium";
    return "high";
}
