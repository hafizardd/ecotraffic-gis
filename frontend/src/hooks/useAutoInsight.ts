"use client";

import { useState } from "react";
import { fetchBangJoAutoInsight } from "@/services/api";
import { createAutoInsight, entityKey, type AutoInsightEntity } from "@/utils/autoInsight";
import type { BangJoAutoInsightReply, BangJoAutoInsightRequest } from "@/types";

const controller = createAutoInsight<BangJoAutoInsightReply>({
    debounceMs: 0,
    loader: async (entity) => {
        const request: BangJoAutoInsightRequest = entity.type === "segment"
            ? { road_segment_id: String(entity.id) }
            : entity.type === "hex"
                ? { hex_id: Number(entity.id), hour: entity.hour ?? null, hour_label: entity.hourLabel ?? null }
                : { stop_id: String(entity.id) };
        try {
            return await fetchBangJoAutoInsight(request);
        } catch (error) {
            return {
                needs_selection: false, answer: null, context_label: null, entity: null, cached: false,
                detail: error instanceof Error ? error.message : "Bang Jo tidak dapat dihubungi. Coba lagi.",
            };
        }
    },
});

// Manual trigger only: the panel never calls the LLM on mount/selection, so
// opening panels or scrubbing the hour slider cannot burn the rate limit.
export function useAutoInsight(entity: AutoInsightEntity) {
    const key = entityKey(entity);
    const [result, setResult] = useState<{ key: string; value: BangJoAutoInsightReply | null } | null>(null);
    const [loading, setLoading] = useState(false);

    const generate = async () => {
        setLoading(true);
        const value = await controller.schedule(entity);
        setResult({ key, value });
        setLoading(false);
    };

    const retry = () => {
        controller.clearCache();
        setResult(null);
        return generate();
    };

    return { reply: result?.key === key ? result.value : null, loading, generate, retry };
}
