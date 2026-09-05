import { useEffect, useState } from "react";
import { fetchSegmentsGeoJSON } from "@/services/api";
import { SegmentFeature } from "@/types";

export default function useSegments() {
    const [segments, setSegments] = useState<SegmentFeature[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
    useEffect(() => {
        let mounted = true;
        fetchSegmentsGeoJSON().then((data) => mounted && setSegments(data.features)).catch((err) => mounted && setError(err instanceof Error ? err : new Error("Gagal memuat segmen"))).finally(() => mounted && setLoading(false));
        return () => { mounted = false; };
    }, []);
    return { segments, loading, error };
}
