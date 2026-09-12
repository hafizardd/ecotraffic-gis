import type { EmissionUpdate, HistoricalCameraEmission } from "@/types";

export interface CameraDisplayValue {
    co2_g_per_min: number | null;
    historical: boolean;
    observed_at: string | null;
    is_interpolated: boolean;
}

// A live WS value always wins; otherwise fall back to the camera's historical
// segment fact. Historical values are display-only and never mixed into live
// aggregates. Kept dependency-free so it is unit-testable under node.
export function cameraDisplayValue(
    live: EmissionUpdate | undefined,
    historical: HistoricalCameraEmission | undefined,
): CameraDisplayValue {
    if (live?.total_co2_g_per_min != null) {
        return {
            co2_g_per_min: Number(live.total_co2_g_per_min), historical: false,
            observed_at: live.captured_at ?? live.period_end ?? live.updated_at ?? null, is_interpolated: false,
        };
    }
    const co2 = historical?.emissions_g_per_min?.co2;
    if (historical && co2 != null) {
        return {
            co2_g_per_min: Number(co2), historical: true,
            observed_at: historical.observed_at, is_interpolated: historical.is_interpolated,
        };
    }
    return { co2_g_per_min: null, historical: false, observed_at: null, is_interpolated: false };
}
