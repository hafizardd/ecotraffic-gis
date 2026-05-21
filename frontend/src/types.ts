export interface CameraProperties {
    id: string;
    name: string;
    camera_id: string;
    stream_url: string;
    is_active: boolean;
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
    car: number;
    motorcycle: number;
    bus: number;
    truck: number;
    total_co_g_per_min: number;
    total_co_kg_per_hr: number;
    total_nox_g_per_min: number;
    total_nox_kg_per_hr: number;
    total_pm_g_per_min: number;
    total_pm_kg_per_hr: number;
    total_nmvoc_g_per_min: number;
    total_nmvoc_kg_per_hr: number;
    cycle_duration_s: number;
}

export interface EmissionRow {
    id: string;
    timestamp: string;
    car: number;
    motorcycle: number;
    bus: number;
    truck: number; 
    total_co_g_per_min: number;
    total_co_kg_per_hr: number;
    total_nox_g_per_min: number;
    total_nox_kg_per_hr: number;
    total_pm_g_per_min: number;
    total_pm_kg_per_hr: number;
    total_nmvoc_g_per_min: number;
    total_nmvoc_kg_per_hr: number;
    cycle_duration_s: number;
}

export interface CameraEmissionsResponse {
    camera_id: string;
    total_records: number;
    emissions: EmissionRow[];
}