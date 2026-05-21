export const API_BASE = process.env.NEXT_PUBLIC_API_URL
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL

import { CameraEmissionsResponse, CameraFeatureCollection } from "@/types";

export async function fetchCameras(): Promise<CameraFeatureCollection> {
    const response = await fetch(`${API_BASE}/api/cameras`)

    if(!response.ok) {
        throw new Error(`Failed to fetch cameras: ${response.statusText}`)
    }

    return response.json();
}

export async function fetchCameraEmissions(
    camera_id: string,
    limit: number = 1
): Promise<CameraEmissionsResponse> {
    const response = await fetch(`${API_BASE}/api/cameras/${camera_id}/emissions?limit=${limit}`);

    if (!response.ok) throw new Error('Failed to fetch emissions');
    
    return response.json();
}
