import { useEffect, useRef, useState } from "react";
import { fetchPois, fetchPopulationZones, fetchSurveyStops } from "@/services/api";
import { SpatialFeatureCollection } from "@/types";

const empty: SpatialFeatureCollection = { type: "FeatureCollection", features: [] };

export default function useSpatialLayers(bbox: string | null, enabled: { pois: boolean; populationZones: boolean; surveyStops: boolean }, poiCategory?: string) {
    const [data, setData] = useState({ pois: empty, populationZones: empty, surveyStops: empty });
    const [loading, setLoading] = useState({ pois: false, populationZones: false, surveyStops: false });
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
            if (enabled.pois) {
                setLoading((p) => ({ ...p, pois: true }));
                fetchPois(bbox ?? undefined, poiCategory || undefined)
                    .then((value) => setData((p) => ({ ...p, pois: value })))
                    .catch((e) => setErrors((p) => ({ ...p, pois: e instanceof Error ? e : new Error(String(e)) })))
                    .finally(() => setLoading((p) => ({ ...p, pois: false })));
            }
            if (enabled.surveyStops) {
                setLoading((p) => ({ ...p, surveyStops: true }));
                fetchSurveyStops(bbox ?? undefined)
                    .then((value) => setData((p) => ({ ...p, surveyStops: value })))
                    .catch((e) => setErrors((p) => ({ ...p, surveyStops: e instanceof Error ? e : new Error(String(e)) })))
                    .finally(() => setLoading((p) => ({ ...p, surveyStops: false })));
            }
        }, 250);
        return () => clearTimeout(timer);
    }, [bbox, enabled.pois, enabled.surveyStops, poiCategory]);

    return { ...data, loading, errors };
}
