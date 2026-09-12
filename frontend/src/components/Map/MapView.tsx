"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sun, Moon, Bus } from "lucide-react";
import Map, { MapRef, NavigationControl, Source, Layer, Popup, Marker, type ViewStateChangeEvent, type MapLayerMouseEvent } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import SidePanel from "../Panel/SidePanel";
import SegmentPanel from "../Panel/SegmentPanel";
import ActivityGridPanel from "../Panel/ActivityGridPanel";
import BusStopPanel from "../Panel/BusStopPanel";
import MapLegend from "./MapLegend";
import Skeleton from "@/components/ui/Skeleton";
import { getCameraTier } from "@/utils/markerColor";
import { cameraDisplayValue, type CameraDisplayValue } from "@/utils/cameraValue";
import { neighborEstimate } from "@/utils/cameraEstimate";
import useCameras from "@/hooks/useCameras";
import { CameraFeature } from "@/types";
import { useEmissionsContext } from "@/context/EmissionsContext";
import useSegments from "@/hooks/useSegments";
import useSpatialLayers from "@/hooks/useSpatialLayers";
import useActivityGrid, { useActivityGridHours } from "@/hooks/useActivityGrid";
import useHistoricalCameraEmissions from "@/hooks/useHistoricalCameraEmissions";
import ActivityHourSlider from "./ActivityHourSlider";
import { nextGridLod, withDay, isWholeRegionLod, adjacentTierToPrefetch, featureInBbox, dataStatusLabel, noDataReasonLabel, GRID_LOD_RESOLUTION, type GridLod } from "@/utils/activityGrid";
import { circleFeature } from "@/utils/geo";
import { fmtDateTimeId, fmtIntId, formatNumber } from "@/utils/format";
import { setSelectedSegmentId as publishSelectedSegment } from "@/utils/selectionStore";
import {
    SEGMENT_COLORS,
    CAMERA_TIER_COLORS,
    FIVE_TIER_COLORS,
    ACTIVITY_SCORE_STOPS,
    breaksToStops,
    MAP_MODES,
    MODE_VISIBILITY,
    DEFAULT_MAP_MODE,
    BUS_STOP_BUFFER_M,
    isMapMode,
    classificationTier,
    interventionColor,
    readableTextOn,
    type MapMode,
} from "@/constants/mapColors";

const TIER_NUM: Record<string, number> = { unavailable: 0, low: 1, medium: 2, high: 3 };
const FRESHNESS_NUM: Record<string, number> = { fresh: 0, aging: 1, stale: 2, unknown: 3 };

const SEGMENT_BUCKET_COLORS = [
    { color: SEGMENT_COLORS.noData, label: "Tidak tersedia" },
    { color: SEGMENT_COLORS.low, label: "< 1.000 g/hr" },
    { color: SEGMENT_COLORS.medium, label: "1.000-4.999" },
    { color: SEGMENT_COLORS.high, label: "5.000-19.999" },
    { color: SEGMENT_COLORS.critical, label: "\u2265 20.000" },
];

interface CameraPointProps {
    camera: CameraFeature;
    emission: number | null;
    freshness: string;
    historical: boolean;
    observedAt: string | null;
    interpolated: boolean;
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
    const [mode, setMode] = useState<MapMode>(() => readStoredMode());
    const [bbox, setBbox] = useState<string | null>(null);
    const [lod, setLod] = useState<GridLod>("fine");
    const [prefetchTier, setPrefetchTier] = useState<GridLod | null>(null);
    const [activityHour, setActivityHour] = useState<string | null>(null);
    const [profileDay, setProfileDay] = useState<string | null>(null);
    const [hoveredHex, setHoveredHex] = useState<{ lon: number; lat: number; id: number | null; count: number | null; status: string | null; reason: string | null } | null>(null);
    const [hoveredHexId, setHoveredHexId] = useState<number | null>(null);
    const [selectedHexId, setSelectedHexId] = useState<number | null>(null);
    const [selectedStopId, setSelectedStopId] = useState<string | null>(null);
    const visible = MODE_VISIBILITY[mode];
    const { surveyStops } = useSpatialLayers(bbox, { surveyStops: visible.surveyStops });
    const historicalCameras = useHistoricalCameraEmissions(visible.cameras);
    const activityHours = useActivityGridHours(visible.activityGrid);
    // The backend serves one static 24h profile; picking a day only relabels the
    // same buckets, so the slider always has a full day to scrub.
    const anchorDay = activityHours.length > 0 ? activityHours[activityHours.length - 1].slice(0, 10) : null;
    const displayHours = useMemo(
        () => activityHours.map((hour) => withDay(hour, profileDay)),
        [activityHours, profileDay],
    );
    const activeHour = visible.activityGrid && displayHours.length > 0
        ? (activityHour && displayHours.includes(activityHour) ? activityHour : displayHours[displayHours.length - 1])
        : null;
    const changeDay = useCallback((nextDay: string) => {
        setProfileDay(nextDay);
        setActivityHour((current) => {
            const reference = current ?? activeHour;
            return reference ? withDay(reference, nextDay) : null;
        });
    }, [activeHour]);
    const { activityGrid, stale: gridStale } = useActivityGrid(bbox, activeHour, visible.activityGrid, lod, activityHours, prefetchTier);
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
        localStorage.setItem("etg-map-mode", mode);
    }, [mode]);

    const cameraGeoJSON = useMemo(() => ({
        type: "FeatureCollection" as const,
        features: cameras.map((camera) => {
            const display = cameraDisplayValue(emissionMap.get(camera.properties.camera_id), historicalCameras.get(camera.properties.camera_id));
            const tier = getCameraTier(display.co2_g_per_min);
            const freshness = display.historical
                ? "fresh"
                : emissionMap.get(camera.properties.camera_id)?.freshness_status ?? camera.properties.freshness_status ?? "unknown";
            return {
                type: "Feature" as const,
                geometry: camera.geometry,
                properties: {
                    camera_id: camera.properties.camera_id,
                    tier: TIER_NUM[tier],
                    freshness: FRESHNESS_NUM[freshness],
                    historical: display.historical ? 1 : 0,
                },
            };
        }),
    }), [cameras, emissionMap, historicalCameras]);

    const activityGridGeoJSON = useMemo(() => ({
        type: "FeatureCollection" as const,
        features: activityGrid.features.map((feature) => ({
            ...feature,
            properties: { ...feature.properties, potential: classificationTier(feature.properties.klasifikasi_potensi) },
        })),
    }), [activityGrid]);

    // Viewport-scoped quantile stops; null when the visible scores have no
    // spread, in which case the fill falls back to the classification tier.
    const activityBreaks = useMemo(() => breaksToStops(activityGrid.breaks), [activityGrid.breaks]);

    // Aggregated tiers ship the whole region (so zoom-out has no empty edges);
    // the count card still reports only what is inside the viewport.
    const displayedCount = useMemo(
        () => activityGrid.features.filter((feature) => featureInBbox(feature, isWholeRegionLod(lod) ? bbox : null)).length,
        [activityGrid.features, lod, bbox],
    );

    // Rebuilt only when the underlying data changes, not on every hover/pan
    // render; the segment set can be large and was previously remapped per render.
    const segmentGeoJSON = useMemo(() => ({ type: "FeatureCollection" as const, features: segments.map((segment) => {
        const update = segmentMap.get(segment.properties.segment_id);
        const pollutantTotals = update?.pollutant_totals ?? segment.properties.pollutant_totals;
        const calculatedTotal = pollutantTotals ? Object.values(pollutantTotals).reduce((sum, value) => sum + Number(value), 0) : null;
        return { ...segment, properties: { ...segment.properties, ...update, total_emission_g_h: update?.total_emission_g_h ?? segment.properties.total_emission_g_h ?? calculatedTotal } };
    }) }), [segments, segmentMap]);

    const camerasById = useMemo(() => new globalThis.Map(cameras.map((camera) => [camera.properties.camera_id, camera])), [cameras]);

    // Zoom is evaluated live (rAF-throttled) so the hexagon size tier swaps as
    // the user scrolls, not only after they stop. Only the tier changes here;
    // the viewport bbox still commits on settle, and the hook serves cached
    // tiers instantly (the adjacent tier is prefetched near each boundary).
    const lodRef = useRef<GridLod>("fine");
    const zoomFrame = useRef<number | null>(null);
    const handleZoom = useCallback((event: ViewStateChangeEvent) => {
        const zoom = event.target.getZoom();
        if (zoomFrame.current != null) return;
        zoomFrame.current = requestAnimationFrame(() => {
            zoomFrame.current = null;
            const nextLod = nextGridLod(zoom, lodRef.current);
            lodRef.current = nextLod;
            setLod(nextLod);
            setPrefetchTier(adjacentTierToPrefetch(zoom, nextLod));
        });
    }, []);

    // Settle still owns the viewport bbox; LOD is re-evaluated so a programmatic
    // easeTo (click-to-zoom) lands on the right tier even without a zoom event.
    const syncViewport = (event: ViewStateChangeEvent) => {
        const bounds = event.target.getBounds();
        const nextBbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
        setBbox((current) => (current === nextBbox ? current : nextBbox));
        const nextLod = nextGridLod(event.target.getZoom(), lodRef.current);
        lodRef.current = nextLod;
        setLod(nextLod);
    };

    // Hover is throttled to one state flush per frame and only commits when a
    // primitive actually changed, so moving across a hex/camera does not
    // re-render MapView (and re-diff every layer) on every mouse event.
    const hoverFrame = useRef<number | null>(null);

    useEffect(() => () => {
        if (hoverFrame.current != null) cancelAnimationFrame(hoverFrame.current);
        if (zoomFrame.current != null) cancelAnimationFrame(zoomFrame.current);
    }, []);

    const handleMouseMove = useCallback((event: MapLayerMouseEvent) => {
        const segmentId = event.features?.find((item) => item.layer?.id === "segments-line")?.properties?.segment_id ?? null;
        const hex = event.features?.find((item) => item.layer?.id === "activity-grid-fill");
        const rawHexId = hex?.properties?.hex_id;
        const hexId = rawHexId == null ? null : Number(rawHexId);
        const hexCount = (hex?.properties?.aggregated_count as number | null) ?? null;
        const hexStatus = (hex?.properties?.data_status as string | null) ?? null;
        const hexReason = (hex?.properties?.no_data_reason as string | null) ?? null;
        const lon = event.lngLat.lng;
        const lat = event.lngLat.lat;
        const cameraFeature = event.features?.find((item) => item.layer?.id === "camera-points");
        let camera: CameraFeature | null = null;
        let coords: [number, number] | null = null;
        if (cameraFeature?.properties?.camera_id) {
            camera = camerasById.get(String(cameraFeature.properties.camera_id)) ?? null;
            coords = camera ? (cameraFeature.geometry as unknown as { coordinates: [number, number] }).coordinates : null;
        }

        if (hoverFrame.current != null) return;
        hoverFrame.current = requestAnimationFrame(() => {
            hoverFrame.current = null;
            setHoveredSegmentId((prev) => (prev === segmentId ? prev : segmentId));
            setHoveredHexId((prev) => (prev === hexId ? prev : hexId));
            setHoveredHex((prev) => {
                if (hexId == null && hexCount == null) return prev === null ? prev : null;
                if (prev && prev.id === hexId && prev.count === hexCount
                    && prev.status === hexStatus && prev.reason === hexReason) return prev;
                return { lon, lat, id: hexId, count: hexCount, status: hexStatus, reason: hexReason };
            });
            setHoveredCamera((prev) => (prev === camera ? prev : camera));
            setHoveredPoint((prev) => {
                if (prev === coords) return prev;
                if (prev && coords && prev[0] === coords[0] && prev[1] === coords[1]) return prev;
                return coords;
            });
        });
    }, [camerasById]);

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

    const cameraPoints: CameraPointProps[] = cameras.map((camera) => {
        const live = emissionMap.get(camera.properties.camera_id);
        const display: CameraDisplayValue = cameraDisplayValue(live, historicalCameras.get(camera.properties.camera_id));
        const freshness = display.historical ? "historical" : live?.freshness_status ?? camera.properties.freshness_status ?? "unknown";
        return {
            camera, emission: display.co2_g_per_min, freshness,
            historical: display.historical, observedAt: display.observed_at, interpolated: display.is_interpolated,
            selected: selectedCamera?.properties.id === camera.properties.id,
        };
    });

    const hoverCounts = {
        fresh: cameraGeoJSON.features.filter((f) => (f.properties as { freshness: number }).freshness === 0).length,
        stale: cameraGeoJSON.features.filter((f) => (f.properties as { freshness: number }).freshness >= 2).length,
        historical: cameraGeoJSON.features.filter((f) => (f.properties as { historical: number }).historical === 1).length,
        total: cameras.length,
    };

    const isAnyPanelOpen = Boolean(selectedCamera || selectedSegmentId || selectedHexId != null || selectedStopId);
    const selectedStop = selectedStopId
        ? surveyStops.features.find((feature) => String(feature.properties.source_id) === selectedStopId) ?? null
        : null;
    // Fall back to the nearest camera with data only when this camera has none.
    const selectedEstimate = selectedCamera
        && !emissionMap.get(selectedCamera.properties.camera_id)
        && !historicalCameras.get(selectedCamera.properties.camera_id)
        ? neighborEstimate(selectedCamera, cameras, emissionMap, historicalCameras)
        : null;
    const bufferGeoJSON = selectedStop
        ? { type: "FeatureCollection" as const, features: [circleFeature(selectedStop.geometry.coordinates as [number, number], BUS_STOP_BUFFER_M)] }
        : null;

    const selectMode = (next: MapMode) => {
        if (next === mode) return;
        setMode(next);
        setSelectedCamera(null);
        setSelectedSegmentId(null);
        publishSelectedSegment(null);
        setSelectedHexId(null);
        setSelectedStopId(null);
        setHoveredCamera(null);
        setHoveredPoint(null);
        setHoveredSegmentId(null);
        setHoveredHex(null);
        setHoveredHexId(null);
    };

    return (
        <div className={`map-panel-layout ${isAnyPanelOpen ? "has-panel" : ""}`}>
        <div className="map-area" ref={mapAreaRef}>
            <Map ref={mapRef} mapLib={maplibregl} mapStyle={`https://basemap.mapid.io/styles/${style}/style.json?key=${geoMapidApiKey}`}
             initialViewState={{ longitude: 110.3695, latitude: -7.7956, zoom: 14 }} style={{ height: "100%", width: "100%" }} interactiveLayerIds={["segments-line", "camera-points", "camera-cluster", "activity-grid-fill"]}
             onMoveEnd={syncViewport}
             onZoom={handleZoom}
             onMouseMove={handleMouseMove}
             onMouseLeave={() => { setHoveredSegmentId(null); setHoveredCamera(null); setHoveredPoint(null); setHoveredHex(null); setHoveredHexId(null); }}
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
                if (hexFeature) {
                    if (hexFeature.properties?.hex_id != null) {
                        setSelectedHexId(Number(hexFeature.properties.hex_id)); setSelectedCamera(null); setSelectedSegmentId(null); publishSelectedSegment(null); setSelectedStopId(null); return;
                    }
                    // Aggregated cell: re-zoom instead of opening a panel with a merged score.
                    const map = mapRef.current?.getMap();
                    map?.easeTo({ center: event.lngLat, zoom: (map.getZoom() ?? 14) + 2, duration: 500 });
                    return;
                }
             }}>
             <NavigationControl position="bottom-right" showCompass={false} />
             {/* Exclusive thematic mode; the basemap and style toggle stay global. */}
             <div className="map-mode-switch" role="tablist" aria-label="Mode peta">
                 {MAP_MODES.map(({ key, label }) => (
                     <button key={key} type="button" role="tab" aria-selected={mode === key}
                         className={`map-mode-tab${mode === key ? " is-active" : ""}`}
                         onClick={() => selectMode(key)}>{label}</button>
                 ))}
             </div>
             {visible.activityGrid && <ActivityHourSlider hours={displayHours} value={activeHour} onChange={setActivityHour}
                 day={profileDay ?? anchorDay} onChangeDay={changeDay} />}
             {visible.activityGrid && (
                 <div className="map-coarse-note">
                     Sel ditampilkan: {displayedCount} · {GRID_LOD_RESOLUTION[lod]}{lod !== "fine" ? " · agregat" : ""}
                 </div>
             )}
             {visible.segments && <Source id="segments" type="geojson" data={segmentGeoJSON}>
                 <Layer id="segments-line" type="line" paint={{ "line-color": ["case", ["==", ["get", "total_emission_g_h"], null], SEGMENT_COLORS.noData, ["step", ["get", "total_emission_g_h"], SEGMENT_COLORS.low, 1000, SEGMENT_COLORS.medium, 5000, SEGMENT_COLORS.high, 20000, SEGMENT_COLORS.critical]], "line-width": ["case", ["==", ["get", "segment_id"], hoveredSegmentId], 6, 3], "line-opacity": ["case", ["==", ["get", "segment_id"], hoveredSegmentId], 0.95, 0.72] }} />
             </Source>}
             {visible.cameras && <Source id="camera-source" type="geojson" data={cameraGeoJSON} cluster clusterMaxZoom={14} clusterRadius={50} clusterProperties={{ maxTier: ["max", ["get", "tier"]] }}>
                <Layer id="camera-cluster" type="circle" filter={["has", "point_count"]} paint={{ "circle-color": ["step", ["get", "maxTier"], CAMERA_TIER_COLORS.unavailable, 1, CAMERA_TIER_COLORS.low, 2, CAMERA_TIER_COLORS.medium, 3, CAMERA_TIER_COLORS.high], "circle-radius": ["step", ["get", "point_count"], 16, 10, 20, 25, 26, 100, 32], "circle-opacity": 0.85 }} />
                <Layer id="camera-cluster-count" type="symbol" filter={["has", "point_count"]} layout={{ "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"] }} paint={{ "text-color": "#ffffff", "text-halo-color": "#000000", "text-halo-width": 1 }} />
                 <Layer id="camera-selected-ring" type="circle" filter={["all", ["!", ["has", "point_count"]], ["==", ["get", "camera_id"], selectedCamera?.properties.camera_id ?? ""]]} paint={{ "circle-color": "#ffffff", "circle-radius": ["step", ["get", "tier"], 16, 1, 17, 2, 19, 3, 21], "circle-opacity": 0.35 }} />
                 {/* Historical badge: a sky ring so a REPLAY value never reads as live. */}
                 <Layer id="camera-historical-ring" type="circle" filter={["all", ["!", ["has", "point_count"]], ["==", ["get", "historical"], 1]]} paint={{ "circle-color": "rgba(0,0,0,0)", "circle-radius": ["step", ["get", "tier"], 17, 1, 18, 2, 20, 3, 22], "circle-stroke-color": "#38bdf8", "circle-stroke-width": 2, "circle-stroke-opacity": 0.9 }} />
                 <Layer id="camera-points" type="circle" filter={["!", ["has", "point_count"]]} paint={{ "circle-color": ["step", ["get", "tier"], CAMERA_TIER_COLORS.unavailable, 1, CAMERA_TIER_COLORS.low, 2, CAMERA_TIER_COLORS.medium, 3, CAMERA_TIER_COLORS.high], "circle-radius": ["step", ["get", "tier"], 11, 1, 12, 2, 14, 3, 16], "circle-stroke-color": ["case", ["==", ["get", "historical"], 1], "#38bdf8", "#ffffff"], "circle-stroke-width": 2.5, "circle-opacity": ["step", ["get", "freshness"], 1, 1, 0.8, 2, 0.35, 3, 0.6] }} />
  </Source>}
             {visible.surveyStops && bufferGeoJSON && (
                 <Source id="bus-stop-buffer" type="geojson" data={bufferGeoJSON as never}>
                     <Layer id="bus-stop-buffer-fill" type="fill" paint={{ "fill-color": "#38bdf8", "fill-opacity": 0.12 }} />
                     <Layer id="bus-stop-buffer-outline" type="line" paint={{ "line-color": "#38bdf8", "line-width": 1.5, "line-dasharray": [2, 2], "line-opacity": 0.85 }} />
                 </Source>
             )}
             {/* Declared last so the grid paints on top of segments/camera/POI. Click priority stays
                 independent of paint order: onClick checks segment/camera hits first regardless. */}
             {visible.activityGrid && <Source id="activity-grid" type="geojson" data={activityGridGeoJSON as never}>
                 {/* Viewport-quantile ramp when the visible scores have spread;
                     otherwise the discrete classification tier, matching the legend. */}
                 <Layer id="activity-grid-fill" type="fill" paint={{
                     "fill-color": ["case",
                         ["==", ["get", "skor_total_ahp"], null],
                         ["step", ["get", "potential"], FIVE_TIER_COLORS.unknown, 1, FIVE_TIER_COLORS.veryLow, 2, FIVE_TIER_COLORS.low, 3, FIVE_TIER_COLORS.medium, 4, FIVE_TIER_COLORS.high, 5, FIVE_TIER_COLORS.veryHigh],
                         ["interpolate", ["linear"], ["get", "skor_total_ahp"], ...(activityBreaks ?? [...ACTIVITY_SCORE_STOPS])]],
                     // `stale` dims the previous frame while the next LOD/bbox
                     // loads, instead of blanking the grid mid-zoom. Fallback
                     // cells are dimmed too, so borrowed scores read as softer.
                     "fill-opacity": ["case",
                         ["==", ["get", "hex_id"], hoveredHexId ?? -1], 0.8,
                         ["==", ["get", "hex_id"], selectedHexId ?? -2], 0.75,
                         ["==", ["get", "data_status"], "fallback"], 0.4,
                         gridStale ? 0.3 : 0.55],
                     "fill-opacity-transition": { duration: 220, delay: 0 },
                     // Constant per-cell outline folded into the fill pass; a
                     // separate line layer doubled the geometry work at 378+ cells.
                     "fill-outline-color": "#ffffff",
                 }} />
                <Layer id="activity-grid-highlight" type="line"
                    filter={["any", ["==", ["get", "hex_id"], hoveredHexId ?? -1], ["==", ["get", "hex_id"], selectedHexId ?? -2]]}
                    paint={{ "line-color": ["case", ["==", ["get", "hex_id"], selectedHexId ?? -2], "#38bdf8", "#e0f2fe"], "line-width": ["case", ["==", ["get", "hex_id"], selectedHexId ?? -2], 3, 2.5], "line-blur": 0.6, "line-opacity": 1 }} />
            </Source>}
             {/* Bus stops render as Lucide badges so the score colour and icon are always legible. */}
             {visible.surveyStops && surveyStops.features.map((feature) => {
                 const [lon, lat] = feature.geometry.coordinates as [number, number];
                 const properties = feature.properties;
                 const selected = String(properties.source_id) === selectedStopId;
                 const label = properties.intervention_class as string | null;
                 // Low score = poor condition = priority for intervention (red).
                 const score = properties.intervention_score == null ? null : Number(properties.intervention_score);
                 const color = interventionColor(score);
                 return (
                     <Marker key={String(properties.source_id)} longitude={lon} latitude={lat} anchor="center">
                         <button
                             type="button"
                             className={`bus-stop-badge${selected ? " is-selected" : ""}`}
                             style={{ background: color, color: readableTextOn(color) }}
                             title={`${properties.title ?? "Halte"}, ${score == null ? label ?? "Belum dinilai" : `skor ${formatNumber(score)}`}`}
                             aria-label={`Halte ${properties.title ?? ""}, ${score == null ? label ?? "belum dinilai" : `skor ${formatNumber(score)}`}`}
                             onClick={(event) => {
                                 event.stopPropagation();
                                 setSelectedStopId(String(properties.source_id));
                                 setSelectedCamera(null); setSelectedSegmentId(null); publishSelectedSegment(null); setSelectedHexId(null);
                             }}
                         >
                             <Bus aria-hidden="true" />
                         </button>
                     </Marker>
                 );
             })}
              {hoveredCamera && hoveredPoint && visible.cameras && (
                <Popup longitude={hoveredPoint[0]} latitude={hoveredPoint[1]} closeButton={false} closeOnClick={false} offset={12} className="popup-dark">
                    <div className="marker-popup">
                        <strong>{hoveredCamera.properties.name}</strong>
                        {hoveredCamera.properties.data_source === "LIVE" && <span className="marker-tracking"><i /> Pelacakan visual</span>}
                        {(() => {
                            const point = cameraPoints.find((p) => p.camera.properties.id === hoveredCamera.properties.id);
                            if (!point) return null;
                            return (
                                <>
                                    <small>CO₂: {point.emission == null ? "N/A" : `${fmtIntId(point.emission)} g/min`}</small>
                                    {point.historical && <small>Nilai segmen pukul {fmtDateTimeId(point.observedAt)}, bukan arus live{point.interpolated ? ", hasil interpolasi jam" : ""}</small>}
                                </>
                            );
                        })()}
                        <small>Klik untuk melihat detail</small>
                    </div>
                </Popup>
              )}
              {(hoveredHex?.id != null || hoveredHex?.count != null) && (
                <Popup longitude={hoveredHex.lon} latitude={hoveredHex.lat} closeButton={false} closeOnClick={false} offset={12} className="popup-dark">
                    <div className="marker-popup">
                        {hoveredHex.count != null ? (
                            <>
                                <strong>Agregat {hoveredHex.count} sel grid</strong>
                                <small>Tampilan perkiraan, bukan skor sel mandiri</small>
                            </>
                        ) : (
                            <>
                                <strong>Hex {hoveredHex.id}</strong>
                                <small>{dataStatusLabel(hoveredHex.status)}</small>
                                {noDataReasonLabel(hoveredHex.reason) && <small>{noDataReasonLabel(hoveredHex.reason)}</small>}
                            </>
                        )}
                    </div>
                </Popup>
              )}
              <MapLegend
                mode={mode}
                segmentBuckets={SEGMENT_BUCKET_COLORS}
                cameraFresh={hoverCounts.fresh}
                cameraStale={hoverCounts.stale}
                cameraHistorical={hoverCounts.historical}
                cameraTotal={hoverCounts.total}
                activityBreaks={activityGrid.breaks ?? null}
            />
              {hoveredSegmentId && (
                  <div className="segment-hover-summary">
                      <strong>{segments.find((segment) => segment.properties.segment_id === hoveredSegmentId)?.properties.name ?? hoveredSegmentId}</strong>
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
            ? <SidePanel camera={selectedCamera} historical={historicalCameras.get(selectedCamera.properties.camera_id) ?? null} estimate={selectedEstimate} onClose={() => setSelectedCamera(null)} />
            : selectedStopId
                ? <BusStopPanel sourceId={selectedStopId} onClose={() => setSelectedStopId(null)} />
                : selectedSegmentId
                    ? <SegmentPanel segmentId={selectedSegmentId} onClose={() => { setSelectedSegmentId(null); publishSelectedSegment(null); }} />
                    : <ActivityGridPanel hexId={selectedHexId} hour={activeHour} onSelectHour={setActivityHour} onClose={() => setSelectedHexId(null)} />}
        </div>
    );
}

function readStoredMode(): MapMode {
    try {
        const raw = localStorage.getItem("etg-map-mode");
        // Migrate the previous 3-mode split (bus / activity) into the combined view.
        if (raw === "bus" || raw === "activity") return "potential";
        return isMapMode(raw) ? raw : DEFAULT_MAP_MODE;
    } catch {
        return DEFAULT_MAP_MODE;
    }
}
