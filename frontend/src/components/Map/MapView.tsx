"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Sun, Moon } from "lucide-react";
import Map, { MapRef, NavigationControl, Source, Layer, Popup } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import SidePanel from "../Panel/SidePanel";
import SegmentPanel from "../Panel/SegmentPanel";
import MapLegend from "./MapLegend";
import { getCameraTier } from "@/utils/markerColor";
import useCameras from "@/hooks/useCameras";
import { CameraFeature, SpatialFeature } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";
import useSegments from "@/hooks/useSegments";
import useSpatialLayers from "@/hooks/useSpatialLayers";
import {
    SEGMENT_COLORS,
    CAMERA_TIER_COLORS,
    DEFAULT_VISIBLE_LAYERS,
    MapLayerKey,
    POPULATION_SCALE,
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
    const [hoveredPopulationDistrict, setHoveredPopulationDistrict] = useState<string | null>(null);
    const [style, setStyle] = useState<"street-2d-building" | "dark">("street-2d-building");
    const [visible, setVisible] = useState<Record<MapLayerKey, boolean>>(() => ({ ...DEFAULT_VISIBLE_LAYERS, ...readStoredLayers() }));
    const [bbox, setBbox] = useState<string | null>(null);
    const [selectedSpatial, setSelectedSpatial] = useState<(SpatialFeature & { kind?: string }) | null>(null);
    const { populationZones, surveyStops } = useSpatialLayers(bbox, { populationZones: visible.populationZones, surveyStops: visible.surveyStops });
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

    if (loading) {
        return (
            <div className="map-state"><span className="loading-spinner" />Memuat lokasi kamera...</div>
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
    const hoveredPopulation = hovered?.population;
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

    const spatialCoords = selectedSpatial?.geometry?.coordinates as unknown;
    const spatialLngLat = Array.isArray(spatialCoords) && spatialCoords.length === 2
        && typeof spatialCoords[0] === "number" && typeof spatialCoords[1] === "number"
        && Number.isFinite(spatialCoords[0]) && Number.isFinite(spatialCoords[1])
        ? (spatialCoords as [number, number])
        : null;

    return (
        <div className={`map-panel-layout ${selectedCamera || selectedSegmentId ? "has-panel" : ""}`}>
        <div className="map-area" ref={mapAreaRef}>
            <Map ref={mapRef} mapLib={maplibregl} mapStyle={`https://basemap.mapid.io/styles/${style}/style.json?key=${geoMapidApiKey}`}
             initialViewState={{ longitude: 110.3695, latitude: -7.7956, zoom: 14 }} style={{ height: "100%", width: "100%" }} interactiveLayerIds={["segments-line", "camera-points", "camera-cluster", "population-fill", "survey-circles"]}
             onMove={(event) => { const b = event.target.getBounds(); setBbox(`${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`); }}
             onMouseMove={(event) => {
                 const segment = event.features?.find((item) => item.layer?.id === "segments-line");
                 setHoveredSegmentId(segment?.properties?.segment_id ?? null);
                 const population = event.features?.find((item) => item.layer?.id === "population-fill");
                 setHoveredPopulationDistrict(population?.properties?.district_name ? String(population.properties.district_name) : null);
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
             onMouseLeave={() => { setHoveredSegmentId(null); setHoveredPopulationDistrict(null); setHoveredCamera(null); setHoveredPoint(null); }}
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
                    if (found) { setSelectedCamera(found); setSelectedSegmentId(null); setHoveredCamera(null); setHoveredPoint(null); return; }
                }
                const feature = event.features?.find((item) => item.layer?.id === "segments-line");
                if (feature?.properties?.segment_id) { setSelectedSegmentId(feature.properties.segment_id); setSelectedCamera(null); return; }
                 const spatial = event.features?.find((item) => ["population-fill", "survey-circles"].includes(item.layer?.id ?? ""));
                 if (spatial) {
                    const geom = spatial.geometry as unknown as { type?: string; coordinates?: unknown };
                    const raw = geom?.coordinates;
                    const isLngLat = Array.isArray(raw) && raw.length === 2
                        && typeof raw[0] === "number" && typeof raw[1] === "number"
                        && Number.isFinite(raw[0]) && Number.isFinite(raw[1]);
                    const coords: [number, number] = isLngLat
                        ? [raw[0] as number, raw[1] as number]
                        : [event.lngLat.lng, event.lngLat.lat];
                     setSelectedSpatial({ type: "Feature", geometry: { type: "Point", coordinates: coords }, properties: spatial.properties as SpatialFeature["properties"], kind: spatial.layer?.id ?? "" });
                     if (spatial.layer?.id === "population-fill" && spatial.properties?.district_name) {
                         setHoveredPopulationDistrict(String(spatial.properties.district_name));
                     }
                 }
             }}>
             <NavigationControl position="bottom-right" showCompass={false} />
              {visible.populationZones && <Source id="population-zones" type="geojson" data={populationZones as never}>
                  <Layer id="population-fill" type="fill" paint={{ "fill-color": ["step", ["coalesce", ["get", "population"], 0], POPULATION_SCALE[0].color, 25000, POPULATION_SCALE[1].color, 100000, POPULATION_SCALE[2].color, 250000, POPULATION_SCALE[3].color], "fill-opacity": 0.2 }} />
                  <Layer id="population-extrusion" type="fill-extrusion" paint={{
                      "fill-extrusion-color": ["case",
                          ["==", ["get", "district_name"], selectedSpatial?.kind === "population-fill" ? String(selectedSpatial.properties.district_name) : ""], "#ddd6fe",
                          ["==", ["get", "district_name"], hoveredPopulationDistrict], "#c4b5fd",
                          ["step", ["coalesce", ["get", "population"], 0], POPULATION_SCALE[0].color, 25000, POPULATION_SCALE[1].color, 100000, POPULATION_SCALE[2].color, 250000, POPULATION_SCALE[3].color],
                      ],
                      "fill-extrusion-height": ["case",
                          ["==", ["get", "district_name"], selectedSpatial?.kind === "population-fill" ? String(selectedSpatial.properties.district_name) : ""], 220,
                          ["==", ["get", "district_name"], hoveredPopulationDistrict], 80,
                          20,
                      ],
                      "fill-extrusion-base": 0,
                      "fill-extrusion-opacity": 0.6,
                  }} />
                  <Layer id="population-outline" type="line" paint={{ "line-color": "#5b21b6", "line-width": ["case", ["==", ["get", "district_name"], selectedSpatial?.kind === "population-fill" ? String(selectedSpatial.properties.district_name) : ""], 3, ["==", ["get", "district_name"], hoveredPopulationDistrict], 2, 1.5], "line-opacity": 0.85 }} />
              </Source>}
             {visible.surveyStops && <Source id="survey-stops" type="geojson" data={surveyStops as never}><Layer id="survey-circles" type="circle" paint={{ "circle-color": "#06b6d4", "circle-radius": 6, "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5 }} /></Source>}
             {visible.segments && <Source id="segments" type="geojson" data={segmentGeoJSON}>
                 <Layer id="segments-line" type="line" paint={{ "line-color": ["case", ["==", ["get", "total_emission_g_h"], null], SEGMENT_COLORS.noData, ["step", ["get", "total_emission_g_h"], SEGMENT_COLORS.low, 1000, SEGMENT_COLORS.medium, 5000, SEGMENT_COLORS.high, 20000, SEGMENT_COLORS.critical]], "line-width": ["case", ["==", ["get", "segment_id"], hoveredSegmentId], 6, 3], "line-opacity": ["case", ["==", ["get", "segment_id"], hoveredSegmentId], 0.95, 0.72] }} />
             </Source>}
             {visible.cameras && <Source id="camera-source" type="geojson" data={cameraGeoJSON} cluster clusterMaxZoom={14} clusterRadius={50} clusterProperties={{ maxTier: ["max", ["get", "tier"]] }}>
                <Layer id="camera-cluster" type="circle" filter={["has", "point_count"]} paint={{ "circle-color": ["step", ["get", "maxTier"], CAMERA_TIER_COLORS.unavailable, 1, CAMERA_TIER_COLORS.low, 2, CAMERA_TIER_COLORS.medium, 3, CAMERA_TIER_COLORS.high], "circle-radius": ["step", ["get", "point_count"], 16, 10, 20, 25, 26, 100, 32], "circle-opacity": 0.85 }} />
                <Layer id="camera-cluster-count" type="symbol" filter={["has", "point_count"]} layout={{ "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"] }} paint={{ "text-color": "#ffffff", "text-halo-color": "#000000", "text-halo-width": 1 }} />
                <Layer id="camera-selected-ring" type="circle" filter={["all", ["!", ["has", "point_count"]], ["==", ["get", "camera_id"], selectedCamera?.properties.camera_id ?? ""]]} paint={{ "circle-color": "#ffffff", "circle-radius": ["step", ["get", "tier"], 16, 1, 17, 2, 19, 3, 21], "circle-opacity": 0.35 }} />
                <Layer id="camera-points" type="circle" filter={["!", ["has", "point_count"]]} paint={{ "circle-color": ["step", ["get", "tier"], CAMERA_TIER_COLORS.unavailable, 1, CAMERA_TIER_COLORS.low, 2, CAMERA_TIER_COLORS.medium, 3, CAMERA_TIER_COLORS.high], "circle-radius": ["step", ["get", "tier"], 11, 1, 12, 2, 14, 3, 16], "circle-stroke-color": "#ffffff", "circle-stroke-width": 2.5, "circle-opacity": ["step", ["get", "freshness"], 1, 1, 0.8, 2, 0.35, 3, 0.6] }} />
</Source>}
              {selectedSpatial && spatialLngLat && (
                 <Popup longitude={spatialLngLat[0]} latitude={spatialLngLat[1]} closeOnClick={false} className="popup-dark" onClose={() => setSelectedSpatial(null)}>
                     {selectedSpatial.kind === "population-fill" ? (
                         <div className="spatial-popup">
                             <span className="spatial-popup-eyebrow">Wilayah populasi</span>
                             <strong className="spatial-popup-title">{String(selectedSpatial.properties.district_name ?? "Kecamatan")}</strong>
                             <div className="spatial-popup-value">{selectedSpatial.properties.population == null ? "Data tidak tersedia" : Number(selectedSpatial.properties.population).toLocaleString("id-ID")}<small>{selectedSpatial.properties.population == null ? "" : " jiwa"}</small></div>
                             <dl className="spatial-popup-meta">
                                 <div><dt>Sumber</dt><dd>{String(selectedSpatial.properties.source ?? "Data wilayah")}</dd></div>
                                 <div><dt>Tahun referensi</dt><dd>{String(selectedSpatial.properties.reference_year ?? "Tidak tersedia")}</dd></div>
                             </dl>
                         </div>
                    ) : selectedSpatial.kind === "survey-circles" ? (
                        <div><strong>{String(selectedSpatial.properties.title ?? "Halte survei")}</strong><p>Skor: {selectedSpatial.properties.score ?? "N/A"} · {selectedSpatial.properties.observed_at ? new Date(String(selectedSpatial.properties.observed_at)).toLocaleString("id-ID") : "Waktu tidak tersedia"}</p>{selectedSpatial.properties.source_id && <p>ID: {String(selectedSpatial.properties.source_id)} · Media: {String(selectedSpatial.properties.media_count ?? 0)}</p>}</div>
                    ) : (
                        <div className="spatial-popup">
                            <span className="spatial-popup-eyebrow">Observasi lapangan</span>
                            <strong className="spatial-popup-title">{String(selectedSpatial.properties.title ?? "Halte survei")}</strong>
                            <dl className="spatial-popup-meta">
                                <div><dt>Skor</dt><dd>{String(selectedSpatial.properties.score ?? "N/A")}</dd></div>
                                <div><dt>Diamati</dt><dd>{selectedSpatial.properties.observed_at ? new Date(String(selectedSpatial.properties.observed_at)).toLocaleString("id-ID") : "Waktu tidak tersedia"}</dd></div>
                                {selectedSpatial.properties.source_id && <div><dt>ID sumber</dt><dd>{String(selectedSpatial.properties.source_id)}</dd></div>}
                                {selectedSpatial.properties.media_count != null && <div><dt>Media</dt><dd>{String(selectedSpatial.properties.media_count)}</dd></div>}
                            </dl>
                        </div>
                    )}
                </Popup>
              )}
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
                      <span>Kecamatan: {hovered?.population_district ?? "Data tidak tersedia"}</span>
                      <span>Populasi wilayah: {hoveredPopulation == null ? "Data tidak tersedia" : `${hoveredPopulation.toLocaleString("id-ID")} jiwa`}</span>
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
        {selectedCamera ? <SidePanel camera={selectedCamera} onClose={() => setSelectedCamera(null)} /> : <SegmentPanel segmentId={selectedSegmentId} onClose={() => setSelectedSegmentId(null)} />}
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
