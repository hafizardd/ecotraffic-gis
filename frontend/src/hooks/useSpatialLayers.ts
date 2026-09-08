import { useEffect, useRef, useState } from "react";
import { fetchPois, fetchPopulationZones, fetchSurveyStops } from "@/services/api";
import { SpatialFeatureCollection } from "@/types";

const empty: SpatialFeatureCollection = { type: "FeatureCollection", features: [] };

function extractPoiCategories(collection: SpatialFeatureCollection): string[] {
    return Array.from(new Set(
        collection.features
            .map((feature) => String(feature.properties.category ?? ""))
            .filter(Boolean),
    )).sort();
}

export default function useSpatialLayers(bbox: string | null, enabled: { pois: boolean; populationZones: boolean; surveyStops: boolean }, poiCategory?: string) {
    const [data, setData] = useState({ pois: empty, populationZones: empty, surveyStops: empty });
    const [poiCategories, setPoiCategories] = useState<string[]>([]);
    const [loading, setLoading] = useState({ pois: false, populationZones: false, surveyStops: false });
    const [errors, setErrors] = useState<Record<string, Error>>({});
    const zonesLoaded = useRef(false);
    const poiRequestId = useRef(0);

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
        const requestId = ++poiRequestId.current;
        const timer = setTimeout(() => {
            if (enabled.pois) {
                const requestedCategory = poiCategory || undefined;
                setLoading((p) => ({ ...p, pois: true }));
                fetchPois(bbox ?? undefined, requestedCategory)
                    .then((value) => {
                        if (requestId !== poiRequestId.current) return;
                        setData((p) => ({ ...p, pois: value }));

                        // Keep the dropdown options from the unfiltered response.
                        // A filtered response only contains the selected category.
                        if (!requestedCategory) setPoiCategories(extractPoiCategories(value));
                    })
                    .catch((e) => {
                        if (requestId !== poiRequestId.current) return;
                        setErrors((p) => ({ ...p, pois: e instanceof Error ? e : new Error(String(e)) }));
                    })
                    .finally(() => {
                        if (requestId === poiRequestId.current) setLoading((p) => ({ ...p, pois: false }));
                    });
            } else {
                setLoading((p) => ({ ...p, pois: false }));
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

    return { ...data, poiCategories, loading, errors };
}
