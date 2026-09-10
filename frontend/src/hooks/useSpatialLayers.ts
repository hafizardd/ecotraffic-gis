import { useEffect, useState } from "react";
import { fetchSurveyStops } from "@/services/api";
import { SpatialFeatureCollection } from "@/types";

const empty: SpatialFeatureCollection = { type: "FeatureCollection", features: [] };

export default function useSpatialLayers(bbox: string | null, enabled: { surveyStops: boolean }) {
    const [surveyStops, setSurveyStops] = useState<SpatialFeatureCollection>(empty);
    const [errors, setErrors] = useState<Record<string, Error>>({});

    useEffect(() => {
        const timer = setTimeout(() => {
            if (enabled.surveyStops) {
                fetchSurveyStops(bbox ?? undefined)
                    .then(setSurveyStops)
                    .catch((e) => setErrors((p) => ({ ...p, surveyStops: e instanceof Error ? e : new Error(String(e)) })));
            }
        }, 250);
        return () => clearTimeout(timer);
    }, [bbox, enabled.surveyStops]);

    return { surveyStops, errors };
}
