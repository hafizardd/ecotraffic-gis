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
    source_mode?: "LIVE" | "HISTORICAL" | "REPLAY" | "SYNTHETIC" | "SNAPSHOT_REAL";
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
    provenance: Record<string, unknown>;
    volume_status?: "calculated" | "estimated" | "unavailable";
    vehicle_count_semantics?: string;
    freshness_status?: string;
    data_age_seconds?: number | null;
    population?: number | null;
    population_district?: string | null;
    population_context?: PopulationContext | null;
}
export interface SpatialFeatureCollection { type: "FeatureCollection"; features: SpatialFeature[]; }
export interface SpatialFeature { type: "Feature"; geometry: { type: string; coordinates: unknown }; properties: Record<string, string | number | null>; }
// WS `segment_update` payload uses `pollutant_totals` (= `pollutant_totals_g_h` in REST detail).
// Map via SegmentPanel liveDetail mapper; do not rename without updating both.
export interface SegmentUpdateData {
    emissions_kg_h?: PollutantRates;
    processed_at?: string;
    calculation_version?: number;
    total_emission_g_h?: number | null; volume_per_hour?: Record<string, number> | null; pollutant_totals?: Record<string, number> | null; calculated_at?: string;
    observed_at?: string | null; data_age_seconds?: number | null; freshness_status?: string;
    population?: number | null; population_district?: string | null; population_context?: PopulationContext | null;
}

export type PollutantKey = "tsp" | "co" | "nox" | "so2" | "hc" | "co2" | "ch4" | "n2o";
export type PollutantRates = Record<PollutantKey, number | null>;
export type VehicleRates = Record<"car" | "motorcycle" | "bus" | "truck", number>;

export interface EmissionAnalyticsFilter {
    timeRange: "1h" | "3h" | "12h" | "24h";
    segmentId: string | null;
    corridorId: string | null;
    from: string | null;
    to: string | null;
}
export interface AnalyticsQuery {
    from: string; to: string; segment_id?: string; corridor_id?: string;
    search?: string; quality_status?: "observed" | "estimated"; source_mode?: string;
}
export type EmissionTrendPoint = Record<`${PollutantKey}_kg_h`, number | null> & {
    timestamp: string; segment_count: number; sample_count: number; estimated_sample_count: number;
};
export type TopEmissionCorridor = {
    rank: number; corridor_id: string; corridor_name: string; segment_ids: string[];
    pollutant: PollutantKey; emission_kg_h: number | null; sample_count: number;
    estimated_sample_count: number; observed_at: string;
} & Record<`${PollutantKey}_kg_h`, number | null>;
export interface PollutantComposition { pollutant: string; key: PollutantKey; kg_h: number | null; }
export interface RealtimeSegmentEmission {
    id: string; segment_id: string; segment_name: string; corridor_id: string; corridor_name: string;
    period_start: string; period_end: string; observed_at: string; processed_at: string;
    calculation_version: number; source_mode: "LIVE" | "HISTORICAL" | "SYNTHETIC" | "REPLAY" | "SNAPSHOT_REAL";
    vehicle_count_semantics: "interval_count" | "snapshot_occupancy" | "vehicles_per_hour" | "unknown";
    calculation_mode: "flow_based_segment" | "live_occupancy_estimate";
    quality_status: "observed" | "estimated";
    freshness_seconds: number; stale_after_seconds: number; freshness_status: "fresh" | "stale";
    emissions_kg_h: PollutantRates; volume_per_hour: VehicleRates | null; vkt_km_h: VehicleRates | null;
    raw_counts: VehicleRates; source_cameras: string[]; source_streams: string[];
    source_observation_count: number; observation_duration_seconds: number; aggregation_policy: string;
    category_pollutant_breakdown_g_h: Record<string, Record<string, number>>;
    calculation_metadata: Record<string, unknown>;
}
export interface HistoryRecordDetail {
    calculation_version: number;
    calculation_mode: string;
    vkt_km_h: VehicleRates | null;
    source_cameras: string[];
    source_streams: string[];
    source_observation_count: number;
    observation_duration_seconds: number;
}
export interface EmissionHistoryRecord {
    id: string;
    period_start: string; period_end: string; observed_at: string; processed_at: string;
    segment_id: string; segment_name: string; corridor_id: string; corridor_name: string;
    source_mode: "LIVE" | "HISTORICAL" | "SYNTHETIC" | "REPLAY" | "SNAPSHOT_REAL";
    quality_status: "observed" | "estimated";
    freshness_status: "fresh" | "stale";
    vehicle_count_semantics: string;
    emissions_kg_h: PollutantRates;
    total_emissions_kg_h: number | null;
    volume_per_hour: VehicleRates | null;
    total_vehicles_per_hour: number | null;
    units: { emissions: string; volume_per_hour: string; vkt_km_h: string };
    detail: HistoryRecordDetail;
}
export interface AnalyticsResponse<T> { from: string; to: string; data: T[]; }
export interface EmissionHistoryResponse extends AnalyticsResponse<EmissionHistoryRecord> {
    total: number; page: number; page_size: number; sort: string; order: "asc" | "desc";
    units: { emissions: string; volume_per_hour: string; vkt_km_h: string };
}
export interface EmissionHistoryDeleteResponse {
    deleted?: number; matched?: number; truncated: boolean;
}
export interface LatestSegmentEmissionsResponse {    timestamp: string; segments: RealtimeSegmentEmission[];
    summary: { emissions_kg_h: PollutantRates; segment_count: number; estimated_segment_count: number;
        freshness_seconds: number | null; stale_after_seconds: number; observed_at: string | null;
        processed_at: string | null; source_mode: "LIVE" | "HISTORICAL";
    };
}
export interface AnalyticsSegmentOption { segment_id: string; segment_name: string; corridor_id: string; corridor_name: string; }
export type VehicleKey = "car" | "motorcycle" | "bus" | "truck";
export type VehicleTotals = Record<VehicleKey, number | null>;
export interface VehicleCompositionSlice { key: VehicleKey; vehicles_per_hour: number | null; share: number | null; }
export interface VehicleRankingRow {
    rank: number; segment_id: string; segment_name: string; corridor_name: string;
    car_veh_h: number | null; motorcycle_veh_h: number | null; bus_veh_h: number | null; truck_veh_h: number | null;
    total_veh_h: number | null; sample_count: number; estimated_sample_count: number;
}
export interface VehicleSeriesPoint {
    timestamp: string; car_veh_h: number | null; motorcycle_veh_h: number | null;
    bus_veh_h: number | null; truck_veh_h: number | null; segment_count: number;
}
export interface VehicleAnalyticsResponse {
    from: string; to: string; bucket: string;
    units: { volume_per_hour: string; vkt_km_h: string };
    totals: VehicleTotals; total_vehicles_per_hour: number | null;
    vkt: VehicleTotals; total_vkt_km_h: number | null;
    composition: VehicleCompositionSlice[];
    ranking: VehicleRankingRow[];
    series: VehicleSeriesPoint[];
    sample_count: number; estimated_sample_count: number;
}
export interface SegmentUpdate { type: "segment_update"; segment_id: string; data: SegmentUpdateData; }

export interface EmissionSummary {
    total_cameras_active: number;
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
    by_vehicle: { car: number; motorcycle: number; bus: number; truck: number };
    last_updated: string | null;
    freshness_status?: string;
    active_cameras?: number;
    live_cameras?: number;
    historical_cameras?: number;
    fresh_camera_states?: number;
    stale_camera_states?: number;
    latest_observation_at?: string | null;
    latest_processing_at?: string | null;
    source?: string;
}

export interface BangJoMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    contextLabel?: string;
    timestamp: string;
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

export interface ActivityGridProperties {
    hex_id: number | null;
    h3_index?: string | null;
    luas_km2: number;
    poi_total: number;
    poi_breakdown: Record<string, number>;
    penduduk: number;
    volume_mean: number;
    norm_volume: number | null;
    norm_poi: number;
    norm_penduduk: number;
    skor_total_ahp: number | null;
    ranking: number | null;
    klasifikasi_potensi: string | null;
    ahp_weight_version: string;
    source: string;
    data_status?: "live" | "static" | "no_data";
    // Live ranking is over the observed hex set, so the denominator can differ
    // from the static 378.
    ranking_total?: number | null;
    // Client-only render fields: `potential` is the 0-5 tier driving the fill
    // expression; coarse LOD sets `aggregated_count` and clears `hex_id`.
    potential?: number;
    aggregated_count?: number;
}

export interface ActivityGridFeature {
    type: "Feature";
    geometry: { type: string; coordinates: unknown };
    properties: ActivityGridProperties;
}

export interface ActivityGridFeatureCollection {
    type: "FeatureCollection";
    features: ActivityGridFeature[];
    // Viewport-scoped quantile cut points for the choropleth; null when the
    // visible scores have no spread (fall back to classification tiers).
    breaks?: number[] | null;
    lod?: "coarse" | "medium" | "sub" | "fine";
    resolution?: number | null;
}

export interface ActivityGridHourPoint {
    hour: string;
    skor_total_ahp: number | null;
    norm_volume: number | null;
    klasifikasi_potensi: string | null;
    data_status: "live" | "static" | "no_data";
}

export interface ActivityGridHourSeries {
    hex_id: number;
    series: ActivityGridHourPoint[];
}

export interface SurveyStopProperties extends Record<string, string | number | null> {
    source_id: string;
    title: string;
    facility_score: number | null;
    environment_score: number | null;
    accessibility_score: number | null;
    intervention_score: number | null;
    intervention_rank: number | null;
    intervention_class: string | null;
}

export interface BusStopDetail {
    source_id: string;
    title: string;
    description: string | null;
    observed_at: string | null;
    media: { url?: string; type?: string }[];
    observer_name: string | null;
    facility_score: number | null;
    pedestrian_access_score: number | null;
    environment_score: number | null;
    user_activity_score: number | null;
    survey_score: number | null;
    score_method: string | null;
    accessibility_score: number | null;
    intervention_score: number | null;
    intervention_rank: number | null;
    intervention_class: string | null;
    accessibility_score_100: number | null;
    condition_score_100: number | null;
    environment_score_100: number | null;
    ahp_total_score: number | null;
    ahp_rank: number | null;
    ahp_classification: string | null;
    ahp_weight_version: string | null;
    facility_checklist: Record<string, boolean> | null;
    damage_indicators: Record<string, boolean> | null;
    poi_breakdown_survey: Record<string, number> | null;
    accessibility_breakdown: { category: string; count: number }[];
    accessibility_buffer_m: number;
}

export interface BangJoAnswer {
    summary: string;
    drivers: string[];
    asi_category: string;
    recommendation: string;
    evidence: string[];
    source?: string;
}

export interface BangJoReply {
    needs_selection: boolean;
    answer: BangJoAnswer | null;
    context_label: string | null;
    candidates?: { road_segment_id: string; name: string; count?: number }[];
    detail?: string;
}
