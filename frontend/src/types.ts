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
