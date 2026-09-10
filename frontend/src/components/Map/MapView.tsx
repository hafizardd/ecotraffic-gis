"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Sun, Moon } from "lucide-react";
import Map, { MapRef, NavigationControl, Source, Layer, Popup } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import SidePanel from "../Panel/SidePanel";
import SegmentPanel from "../Panel/SegmentPanel";
import ActivityGridPanel from "../Panel/ActivityGridPanel";
import BusStopPanel from "../Panel/BusStopPanel";
import MapLegend from "./MapLegend";
import Skeleton from "@/components/ui/Skeleton";
import { getCameraTier } from "@/utils/markerColor";
import useCameras from "@/hooks/useCameras";
import { CameraFeature } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";
import useSegments from "@/hooks/useSegments";
import useSpatialLayers from "@/hooks/useSpatialLayers";
import useActivityGrid from "@/hooks/useActivityGrid";
import { setSelectedSegmentId as publishSelectedSegment } from "@/utils/selectionStore";
import {
    SEGMENT_COLORS,
    CAMERA_TIER_COLORS,
    FIVE_TIER_COLORS,
    DEFAULT_VISIBLE_LAYERS,
    MapLayerKey,
    classificationTier,
} from "@/constants/mapColors";

const TIER_NUM: Record<string, number> = { unavailable: 0, low: 1, medium: 2, high: 3 };
const FRESHNESS_NUM: Record<string, number> = { fresh: 0, aging: 1, stale: 2, unknown: 3 };

interface CameraPointProps {
    camera: CameraFeature;
    emission: number | null;
    freshness: string;
    selected?: boolean;
}

export default function MapView() {
    const { cameras, loading, error } = useCameras();
    const { emissionMap, segmentMap } = useEmissionsContext();
    const { segments } = useSegments();
    const [selectedCamera, setSelectedCamera] = useState<CameraFeature | null>(null);
    const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
    const [hoveredSegmentId, setHoveredSegmentId] = useState<string | null>(null);
    const [hoveredCamera, setHoveredCamera] = useState<CameraFeature | null>(null);
    const [hoveredPoint, setHoveredPoint] = useState<[number, number] | null>(null);
    const [style, setStyle] = useState<"street-2d-building" | "dark">("street-2d-building");
    const [visible, setVisible] = useState<Record<MapLayerKey, boolean>>(() => ({ ...DEFAULT_VISIBLE_LAYERS, ...readStoredLayers() }));
    const [bbox, setBbox] = useState<string | null>(null);
    const [selectedHexId, setSelectedHexId] = useState<number | null>(null);
    const [selectedStopId, setSelectedStopId] = useState<string | null>(null);
    const { surveyStops } = useSpatialLayers(bbox, { surveyStops: visible.surveyStops });
    const { activityGrid } = useActivityGrid(bbox, visible.activityGrid);
    const isDark = style === "dark";
    const mapRef = useRef<MapRef>(null);
    const mapAreaRef = useRef<HTMLDivElement>(null);
    const geoMapidApiKey = process.env.NEXT_PUBLIC_GEOMAPID_API_KEY;

    useEffect(() => {
        const area = mapAreaRef.current;
        if (!area) return;
        const observer = new ResizeObserver(() => mapRef.current?.resize());
        observer.observe(area);
        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        localStorage.setItem("etg-visible-layers", JSON.stringify(visible));
    }, [visible]);

    const cameraGeoJSON = useMemo(() => ({
        type: "FeatureCollection" as const,
        features: cameras.map((camera) => {
            const emission = emissionMap.get(camera.properties.camera_id);
            const co2 = emission?.total_co2_g_per_min ?? null;
            const tier = getCameraTier(co2 == null ? null : Number(co2));
            const freshness = emission?.freshness_status ?? camera.properties.freshness_status ?? "unknown";
            return {
                type: "Feature" as const,
                geometry: camera.geometry,
                properties: {
                    camera_id: camera.properties.camera_id,
                    tier: TIER_NUM[tier],
                    freshness: FRESHNESS_NUM[freshness],
                },
            };
        }),
    }), [cameras, emissionMap]);

    const activityGridGeoJSON = useMemo(() => ({
        type: "FeatureCollection" as const,
        features: activityGrid.features.map((feature) => ({
            ...feature,
            properties: { ...feature.properties, potential: classificationTier(feature.properties.klasifikasi_potensi) },
        })),
    }), [activityGrid]);

    const surveyStopGeoJSON = useMemo(() => ({
        type: "FeatureCollection" as const,
        features: surveyStops.features.map((feature) => ({
            ...feature,
            properties: { ...feature.properties, intervention: classificationTier(feature.properties.intervention_class as string | null) },
        })),
    }), [surveyStops]);

    if (loading) {
        return (
            <div className="map-panel-layout">
                <div className="map-area"><Skeleton height="100%" width="100%" radius={12} /></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="map-state error-state"><strong>Peta tidak dapat dimuat</strong><span>{error.message}</span></div>
        );
    }

    const camerasById = new globalThis.Map(cameras.map((camera) => [camera.properties.camera_id, camera]));

    const cameraPoints: CameraPointProps[] = cameras.map((camera) => {
        const emission = emissionMap.get(camera.properties.camera_id);
        const co2 = emission?.total_co2_g_per_min ?? null;
        const freshness = emission?.freshness_status ?? camera.properties.freshness_status ?? "unknown";
        return { camera, emission: co2 == null ? null : Number(co2), freshness, selected: selectedCamera?.properties.id === camera.properties.id };
    });

    const segmentGeoJSON = { type: "FeatureCollection" as const, features: segments.map((segment) => {
        const update = segmentMap.get(segment.properties.segment_id);
        const pollutantTotals = update?.pollutant_totals ?? segment.properties.pollutant_totals;
        const calculatedTotal = pollutantTotals ? Object.values(pollutantTotals).reduce((sum, value) => sum + Number(value), 0) : null;
        return { ...segment, properties: { ...segment.properties, ...update, total_emission_g_h: update?.total_emission_g_h ?? segment.properties.total_emission_g_h ?? calculatedTotal } };
    }) };
    const hovered = segmentGeoJSON.features.find((feature) => feature.properties.segment_id === hoveredSegmentId)?.properties;
    const hoveredFreshness = hovered?.freshness_status ?? "unknown";
    const segmentBucketColors = [
        { color: SEGMENT_COLORS.noData, label: "Tidak tersedia" },
        { color: SEGMENT_COLORS.low, label: "< 1.000 g/hr" },
        { color: SEGMENT_COLORS.medium, label: "1.000-4.999" },
        { color: SEGMENT_COLORS.high, label: "5.000-19.999" },
        { color: SEGMENT_COLORS.critical, label: "\u2265 20.000" },
    ];

    const toggleLayer = (key: MapLayerKey) => setVisible((prev) => ({ ...prev, [key]: !prev[key] }));

    const hoverCounts = {
        fresh: cameraGeoJSON.features.filter((f) => (f.properties as { freshness: number }).freshness === 0).length,
        stale: cameraGeoJSON.features.filter((f) => (f.properties as { freshness: number }).freshness >= 2).length,
        total: cameras.length,
    };

    const isAnyPanelOpen = Boolean(selectedCamera || selectedSegmentId || selectedHexId != null || selectedStopId);

    return (
        <div className={`map-panel-layout ${isAnyPanelOpen ? "has-panel" : ""}`}>
        <div className="map-area" ref={mapAreaRef}>
            <Map ref={mapRef} mapLib={maplibregl} mapStyle={`https://basemap.mapid.io/styles/${style}/style.json?key=${geoMapidApiKey}`}
             initialViewState={{ longitude: 110.3695, latitude: -7.7956, zoom: 14 }} style={{ height: "100%", width: "100%" }} interactiveLayerIds={["segments-line", "camera-points", "camera-cluster", "survey-circles", "activity-grid-fill"]}
             onMove={(event) => { const b = event.target.getBounds(); setBbox(`${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`); }}
             onMouseMove={(event) => {
                 const segment = event.features?.find((item) => item.layer?.id === "segments-line");
                 setHoveredSegmentId(segment?.properties?.segment_id ?? null);
                 const camera = event.features?.find((item) => item.layer?.id === "camera-points");
                if (camera?.properties?.camera_id) {
                    const found = camerasById.get(String(camera.properties.camera_id));
                    const coords = (camera.geometry as unknown as { coordinates: [number, number] }).coordinates;
                    setHoveredCamera(found ?? null);
                    setHoveredPoint(coords);
                } else {
                    setHoveredCamera(null);
                    setHoveredPoint(null);
                }
            }}
             onMouseLeave={() => { setHoveredSegmentId(null); setHoveredCamera(null); setHoveredPoint(null); }}
            onClick={(event) => {
                const cameraCluster = event.features?.find((item) => item.layer?.id === "camera-cluster");
                if (cameraCluster?.properties?.cluster_id != null) {
                    const map = mapRef.current?.getMap();
                    const source = map?.getSource("camera-source") as unknown as { getClusterExpansionZoom?: (id: number, cb: (err: unknown, zoom: number) => void) => void } | undefined;
                    const id = Number(cameraCluster.properties.cluster_id);
                     if (source?.getClusterExpansionZoom) source.getClusterExpansionZoom(id, (err, zoom) => { if (!err && map) map.easeTo({ center: event.lngLat, zoom, duration: 500 }); });
                    else map?.easeTo({ center: event.lngLat, zoom: (map.getZoom() ?? 14) + 2 });
                    return;
                }
                const camera = event.features?.find((item) => item.layer?.id === "camera-points");
                if (camera?.properties?.camera_id) {
                    const found = camerasById.get(String(camera.properties.camera_id));
                    if (found) { setSelectedCamera(found); setSelectedSegmentId(null); publishSelectedSegment(null); setSelectedHexId(null); setSelectedStopId(null); setHoveredCamera(null); setHoveredPoint(null); return; }
                }
                const feature = event.features?.find((item) => item.layer?.id === "segments-line");
                if (feature?.properties?.segment_id) {
                    setSelectedSegmentId(feature.properties.segment_id); publishSelectedSegment(feature.properties.segment_id);
                    setSelectedCamera(null); setSelectedHexId(null); setSelectedStopId(null); return;
                }
                const hexFeature = event.features?.find((item) => item.layer?.id === "activity-grid-fill");
                if (hexFeature?.properties?.hex_id != null) {
                    setSelectedHexId(Number(hexFeature.properties.hex_id)); setSelectedCamera(null); setSelectedSegmentId(null); publishSelectedSegment(null); setSelectedStopId(null); return;
                }
                const spatial = event.features?.find((item) => item.layer?.id === "survey-circles");
                if (spatial?.properties?.source_id) {
                    setSelectedStopId(String(spatial.properties.source_id)); setSelectedCamera(null); setSelectedSegmentId(null); publishSelectedSegment(null); setSelectedHexId(null);
                }
             }}>
             <NavigationControl position="bottom-right" showCompass={false} />
             {visible.activityGrid && <Source id="activity-grid" type="geojson" data={activityGridGeoJSON as never}>
                 <Layer id="activity-grid-fill" type="fill" paint={{ "fill-color": ["step", ["get", "potential"], FIVE_TIER_COLORS.unknown, 1, FIVE_TIER_COLORS.veryLow, 2, FIVE_TIER_COLORS.low, 3, FIVE_TIER_COLORS.medium, 4, FIVE_TIER_COLORS.high, 5, FIVE_TIER_COLORS.veryHigh], "fill-opacity": 0.55 }} />
                 <Layer id="activity-grid-outline" type="line" paint={{ "line-color": "#ffffff", "line-width": 0.5, "line-opacity": 0.5 }} />
             </Source>}
             {visible.surveyStops && <Source id="survey-stops" type="geojson" data={surveyStopGeoJSON as never}><Layer id="survey-circles" type="circle" paint={{ "circle-color": ["step", ["get", "intervention"], FIVE_TIER_COLORS.unknown, 1, FIVE_TIER_COLORS.veryLow, 2, FIVE_TIER_COLORS.low, 3, FIVE_TIER_COLORS.medium, 4, FIVE_TIER_COLORS.high, 5, FIVE_TIER_COLORS.veryHigh], "circle-radius": ["case", ["==", ["get", "source_id"], selectedStopId ?? ""], 9, ["step", ["get", "intervention"], 6, 4, 8, 5, 10]], "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5 }} /></Source>}
             {visible.segments && <Source id="segments" type="geojson" data={segmentGeoJSON}>
                 <Layer id="segments-line" type="line" paint={{ "line-color": ["case", ["==", ["get", "total_emission_g_h"], null], SEGMENT_COLORS.noData, ["step", ["get", "total_emission_g_h"], SEGMENT_COLORS.low, 1000, SEGMENT_COLORS.medium, 5000, SEGMENT_COLORS.high, 20000, SEGMENT_COLORS.critical]], "line-width": ["case", ["==", ["get", "segment_id"], hoveredSegmentId], 6, 3], "line-opacity": ["case", ["==", ["get", "segment_id"], hoveredSegmentId], 0.95, 0.72] }} />
             </Source>}
             {visible.cameras && <Source id="camera-source" type="geojson" data={cameraGeoJSON} cluster clusterMaxZoom={14} clusterRadius={50} clusterProperties={{ maxTier: ["max", ["get", "tier"]] }}>
                <Layer id="camera-cluster" type="circle" filter={["has", "point_count"]} paint={{ "circle-color": ["step", ["get", "maxTier"], CAMERA_TIER_COLORS.unavailable, 1, CAMERA_TIER_COLORS.low, 2, CAMERA_TIER_COLORS.medium, 3, CAMERA_TIER_COLORS.high], "circle-radius": ["step", ["get", "point_count"], 16, 10, 20, 25, 26, 100, 32], "circle-opacity": 0.85 }} />
                <Layer id="camera-cluster-count" type="symbol" filter={["has", "point_count"]} layout={{ "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"] }} paint={{ "text-color": "#ffffff", "text-halo-color": "#000000", "text-halo-width": 1 }} />
                <Layer id="camera-selected-ring" type="circle" filter={["all", ["!", ["has", "point_count"]], ["==", ["get", "camera_id"], selectedCamera?.properties.camera_id ?? ""]]} paint={{ "circle-color": "#ffffff", "circle-radius": ["step", ["get", "tier"], 16, 1, 17, 2, 19, 3, 21], "circle-opacity": 0.35 }} />
                <Layer id="camera-points" type="circle" filter={["!", ["has", "point_count"]]} paint={{ "circle-color": ["step", ["get", "tier"], CAMERA_TIER_COLORS.unavailable, 1, CAMERA_TIER_COLORS.low, 2, CAMERA_TIER_COLORS.medium, 3, CAMERA_TIER_COLORS.high], "circle-radius": ["step", ["get", "tier"], 11, 1, 12, 2, 14, 3, 16], "circle-stroke-color": "#ffffff", "circle-stroke-width": 2.5, "circle-opacity": ["step", ["get", "freshness"], 1, 1, 0.8, 2, 0.35, 3, 0.6] }} />
 </Source>}
              {hoveredCamera && hoveredPoint && visible.cameras && (
                <Popup longitude={hoveredPoint[0]} latitude={hoveredPoint[1]} closeButton={false} closeOnClick={false} offset={12} className="popup-dark">
                    <div className="marker-popup">
                        <strong>{hoveredCamera.properties.name}</strong>
                        {hoveredCamera.properties.data_source === "LIVE" && <span className="marker-tracking"><i /> Pelacakan visual</span>}
                        {(() => {
                            const point = cameraPoints.find((p) => p.camera.properties.id === hoveredCamera.properties.id);
                            return point ? <small>CO₂: {point.emission == null ? "N/A" : `${point.emission.toFixed(0)} g/min`} · {point.freshness}</small> : null;
                        })()}
                        <small>Klik untuk melihat detail</small>
                    </div>
                </Popup>
              )}
              <MapLegend
                visible={visible}
                onToggle={toggleLayer}
                segmentBuckets={segmentBucketColors}
                cameraFresh={hoverCounts.fresh}
                cameraStale={hoverCounts.stale}
                cameraTotal={hoverCounts.total}
            />
              {hoveredSegmentId && (
                  <div className="segment-hover-summary">
                      <strong>{hoveredSegmentId}</strong>
                      <span>Data: {hoveredFreshness}</span>
                  </div>
              )}
              <button
                onClick={() => setStyle(s => s === "street-2d-building" ? "dark" : "street-2d-building")}
                className="map-style-toggle"
            >
                {isDark ? (
                    <Sun aria-hidden="true" />
                ) : (
                    <Moon aria-hidden="true" />
                )}
                {isDark ? "Peta terang" : "Peta gelap"}
            </button>
         </Map>
        </div>
        {selectedCamera
            ? <SidePanel camera={selectedCamera} onClose={() => setSelectedCamera(null)} />
            : selectedStopId
                ? <BusStopPanel sourceId={selectedStopId} onClose={() => setSelectedStopId(null)} />
                : selectedSegmentId
                    ? <SegmentPanel segmentId={selectedSegmentId} onClose={() => { setSelectedSegmentId(null); publishSelectedSegment(null); }} />
                    : <ActivityGridPanel hexId={selectedHexId} onClose={() => setSelectedHexId(null)} />}
        </div>
    );
}

function readStoredLayers(): Partial<Record<MapLayerKey, boolean>> {
    try {
        const raw = localStorage.getItem("etg-visible-layers");
        if (!raw) return {};
        const parsed = JSON.parse(raw) as Record<string, unknown>;
        return Object.fromEntries(Object.entries(parsed).filter(([key]) => key in DEFAULT_VISIBLE_LAYERS && typeof parsed[key] === "boolean")) as Partial<Record<MapLayerKey, boolean>>;
    } catch {
        return {};
    }
}
