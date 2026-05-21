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