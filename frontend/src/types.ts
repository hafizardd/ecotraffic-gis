export interface CameraProperties {
    id: string;
    name: string;
    camera_id: string;
    stream_url: string;
    is_active: boolean;
    status: "active" | "degraded" | "offline";
    failure_count: number;
    last_sample_at: string | null;
    last_success_at: string | null;
    last_error_at: string | null;
    freshness_status: "fresh" | "aging" | "stale" | "unknown";
    data_age_seconds: number | null;
    created_at: string;
    data_source?: "LIVE" | "HISTORICAL";
}

export interface CameraFeature {
    type: "Feature";
    geometry: {
        type: "Point";
        coordinates: [number, number];
    };
    properties: CameraProperties;
}

export interface CameraFeatureCollection {
    type: "FeatureCollection";
    features: CameraFeature[];
}

export interface EmissionUpdate {
    type?: "emission_update";
    camera_id: string;
    timestamp: string;
    captured_at?: string;
    updated_at?: string;
    period_start?: string;
    period_end?: string;
    sample_count?: number;
    aggregation_method?: "arithmetic_mean_of_snapshot_counts";
    vehicle_count_semantics?: "mean_observed_snapshot_count";
    freshness_status?: "fresh" | "aging" | "stale" | "unknown";
    data_age_seconds?: number | null;
    frame_acquisition_latency_s?: number;
    queue_wait_s?: number;
    inference_latency_s?: number;
    batch_wait_s?: number;
    batch_inference_latency_s?: number;
    batch_size?: number;
    aggregation_status?: "collecting" | "failed";
    aggregation_window_seconds?: number;
    aggregation_period_start?: string;
    aggregation_period_end?: string;
    aggregation_sample_count?: number;
    aggregation_latency_s?: number;
    job_id?: string;
    car: number;
    motorcycle: number;
    bus: number;
    truck: number;
    total_tsp_g_per_min: number;
    total_tsp_kg_per_hr: number;
    total_nox_g_per_min: number;
    total_nox_kg_per_hr: number;
    total_so2_g_per_min: number;
    total_so2_kg_per_hr: number;
    total_hc_g_per_min: number;
    total_hc_kg_per_hr: number;
    total_co_g_per_min: number;
    total_co_kg_per_hr: number;
    total_co2_g_per_min: number;
    total_co2_kg_per_hr: number;
    total_ch4_g_per_min: number;
    total_ch4_kg_per_hr: number;
    total_n2o_g_per_min: number;
    total_n2o_kg_per_hr: number;
    cycle_duration_s: number;
    source_mode?: "LIVE" | "HISTORICAL" | "REPLAY" | "SYNTHETIC";
    processed_at?: string;
    calculation_version?: string;
    source?: "tracking" | "snapshot";
    occupancy?: Record<string, number>;
    flow_exits?: Record<string, number>;
    instant_emission?: Record<string, number>;
}

export interface EmissionRow {
    id: string;
    timestamp: string;
    car: number;
    motorcycle: number;
    bus: number;
    truck: number; 
    total_tsp_g_per_min: number;
    total_tsp_kg_per_hr: number;
    total_nox_g_per_min: number;
    total_nox_kg_per_hr: number;
    total_so2_g_per_min: number;
    total_so2_kg_per_hr: number;
    total_hc_g_per_min: number;
    total_hc_kg_per_hr: number;
    total_co_g_per_min: number;
    total_co_kg_per_hr: number;
    total_co2_g_per_min: number;
    total_co2_kg_per_hr: number;
    total_ch4_g_per_min: number;
    total_ch4_kg_per_hr: number;
    total_n2o_g_per_min: number;
    total_n2o_kg_per_hr: number;
    cycle_duration_s: number;
}

export interface CameraEmissionsResponse {
    camera_id: string;
    total_records: number;
    emissions: EmissionRow[];
}

export interface SegmentProperties {
    segment_id: string;
    name: string;
    length_km: number;
    decision_score: number | null;
    priority: string | null;
    pollutant_totals: Record<string, number> | null;
    volume_per_hour: Record<string, number> | null;
    total_emission_g_h: number | null;
    freshness_status?: "fresh" | "aging" | "stale" | "unknown";
    data_age_seconds?: number | null;
    vehicle_count_semantics?: string;
    source_cameras?: string[];
    population?: number | null;
    population_district?: string | null;
    population_context?: PopulationContext | null;
    spatial_criteria_status?: string;
    k3_k4_k5_status?: Record<string, string>;
    k5_raw_population_density?: number | null;
    period_start?: string | null;
    period_end?: string | null;
    observed_at?: string | null;
    calculated_at?: string | null;
    source_streams?: string[];
    aggregation_policy?: string | null;
    source_observation_count?: number | null;
    volume_status?: string;
    calculation_version?: number | null;
}
export interface PopulationContext {
    primary?: { district_name?: string; population?: number | null; method?: string } | null;
    intersecting?: { district_name: string; population: number | null; overlap_share: number | null }[];
    buffer_distance_m?: number;
    source?: string;
    calculated_at?: string;
}
export interface SegmentFeature { type: "Feature"; geometry: { type: "LineString"; coordinates: [number, number][] }; properties: SegmentProperties; }
export interface SegmentFeatureCollection { type: "FeatureCollection"; features: SegmentFeature[]; }
export interface SegmentEmissionDetail {
    road_segment_id: string; name: string; length_km: number; period_start: string | null; period_end: string | null; calculated_at: string | null;
    raw_counts: Record<string, unknown> | null; volume_per_hour: Record<string, number> | null; vkt_km_h: Record<string, number> | null;
    pollutant_totals_g_h: Record<string, number> | null; category_pollutant_breakdown_g_h: Record<string, unknown> | null;
    raw_criteria: Record<string, unknown> | null; normalized_criteria: Record<string, unknown> | null;
    decision_score: number | null; priority: string | null; spatial_criteria_status: string;
    provenance: Record<string, unknown>; ahp_metadata: Record<string, unknown> | null;
    volume_status?: "calculated" | "estimated" | "unavailable";
    vehicle_count_semantics?: string;
    freshness_status?: string;
    data_age_seconds?: number | null;
    population?: number | null;
    population_district?: string | null;
    population_context?: PopulationContext | null;
    spatial_criteria_details?: Record<string, unknown> | null;
}
export interface SpatialFeatureCollection { type: "FeatureCollection"; features: SpatialFeature[]; }
export interface SpatialFeature { type: "Feature"; geometry: { type: string; coordinates: unknown }; properties: Record<string, string | number | null>; }
export type SpatialLayerData = { populationZones: SpatialFeatureCollection; surveyStops: SpatialFeatureCollection };
// WS `segment_update` payload uses `pollutant_totals` (= `pollutant_totals_g_h` in REST detail).
// Map via SegmentPanel liveDetail mapper; do not rename without updating both.
export interface SegmentUpdateData {
    decision_score?: number | null; priority?: string | null; total_emission_g_h?: number | null; volume_per_hour?: Record<string, number> | null; pollutant_totals?: Record<string, number> | null; calculated_at?: string; spatial_criteria_status?: string;
    observed_at?: string | null; data_age_seconds?: number | null; freshness_status?: string;
    population?: number | null; population_district?: string | null; population_context?: PopulationContext | null;
}
export interface SegmentUpdate { type: "segment_update"; segment_id: string; data: SegmentUpdateData; }

export interface EmissionSummary {
    total_cameras_active: number;
    by_vehicle: { car: number; motorcycle: number; bus: number; truck: number };
    last_updated: string | null;
    freshness_status?: string;
    active_cameras?: number;
    live_cameras?: number;
    [key: string]: unknown;
}

export interface ChartPoint {
    timestamp: string;
    tsp: number;
    nox: number;
    so2: number;
    hc: number;
    co: number;
    co2: number;
    ch4: number;
    n2o: number;
}
