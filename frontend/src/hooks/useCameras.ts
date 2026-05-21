import { useState, useEffect } from "react";
import { fetchCameras, CameraFeature } from "@/services/api";

export default function useCameras() {
    const [cameras, setCameras] = useState<CameraFeature[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null)

    useEffect(() => {
        fetchCameras()
            .then((data) => setCameras(data.features))
            .catch((err) => setError(err))
            .finally(() => setLoading(false))
    }, [])

    return {cameras, loading, error};
}