export function getMarkerColor(co_g_per_min: number): string {
    if (co_g_per_min < 500) {
        return "#22c55e"
    } else if (co_g_per_min >= 500 && co_g_per_min <= 1500) {
        return "#f59e0b"
    } else {
        return "#ef4444"
    }
}