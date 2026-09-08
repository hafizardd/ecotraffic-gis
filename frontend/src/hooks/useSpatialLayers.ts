import { useEffect, useRef, useState } from "react";
import { fetchPopulationZones, fetchSurveyStops } from "@/services/api";
import { SpatialFeatureCollection } from "@/types";

const empty: SpatialFeatureCollection = { type: "FeatureCollection", features: [] };

export default function useSpatialLayers(bbox: string | null, enabled: { populationZones: boolean; surveyStops: boolean }) {
    const [data, setData] = useState({ populationZones: empty, surveyStops: empty });
    const [loading, setLoading] = useState({ populationZones: false, surveyStops: false });
    const [errors, setErrors] = useState<Record<string, Error>>({});
    const zonesLoaded = useRef(false);

    useEffect(() => {
        if (!enabled.populationZones || zonesLoaded.current) return;
        setLoading((p) => ({ ...p, populationZones: true }));
        fetchPopulationZones()
            .then((value) => {
                zonesLoaded.current = true;
                setData((p) => ({ ...p, populationZones: value }));
            })
            .catch((e) => setErrors((p) => ({ ...p, populationZones: e instanceof Error ? e : new Error(String(e)) })))
            .finally(() => setLoading((p) => ({ ...p, populationZones: false })));
    }, [enabled.populationZones]);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (enabled.surveyStops) {
                setLoading((p) => ({ ...p, surveyStops: true }));
                fetchSurveyStops(bbox ?? undefined)
                    .then((value) => setData((p) => ({ ...p, surveyStops: value })))
                    .catch((e) => setErrors((p) => ({ ...p, surveyStops: e instanceof Error ? e : new Error(String(e)) })))
                    .finally(() => setLoading((p) => ({ ...p, surveyStops: false })));
            }
        }, 250);
        return () => clearTimeout(timer);
    }, [bbox, enabled.surveyStops]);

    return { ...data, loading, errors };
}
