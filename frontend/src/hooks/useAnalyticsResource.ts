"use client";
import { useEffect, useState } from "react";

export default function useAnalyticsResource<T>(key: string, load: (signal: AbortSignal) => Promise<T>) {
    const [result, setResult] = useState<{ key: string; data?: T; error?: string }>({ key: "" });
    useEffect(() => {
        const controller = new AbortController();
        load(controller.signal).then((data) => {
            if (!controller.signal.aborted) setResult({ key, data });
        }).catch((error: Error) => {
            if (!controller.signal.aborted) setResult({ key, error: error.message });
        });
        return () => controller.abort();
    }, [key, load]);
    return result.key === key ? { ...result, loading: false } : { loading: true, data: undefined, error: undefined };
}
