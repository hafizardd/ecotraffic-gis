import { useEffect, useState } from "react";
import { fetchHistoricalCameraEmissions } from "@/services/api";
import { HistoricalCameraEmission } from "@/types";

// One cached fetch of the latest non-LIVE value per mapped camera. Used to color
// historical CCTV points; a live WS value always takes precedence in the caller.
export default function useHistoricalCameraEmissions(enabled: boolean): Map<string, HistoricalCameraEmission> {
    const [cameras, setCameras] = useState<Map<string, HistoricalCameraEmission>>(new Map());

    useEffect(() => {
        if (!enabled) return;
        const controller = new AbortController();
        fetchHistoricalCameraEmissions(controller.signal)
            .then((value) => {
                const next = new Map<string, HistoricalCameraEmission>();
                for (const item of value.cameras) next.set(item.camera_id, item);
                setCameras(next);
            })
            .catch(() => {});
        return () => controller.abort();
    }, [enabled]);

    return cameras;
}
