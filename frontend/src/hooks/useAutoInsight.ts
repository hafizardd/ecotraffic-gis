"use client";

import { useEffect, useState } from "react";
import { fetchBangJoAutoInsight } from "@/services/api";
import { createAutoInsight, entityKey, type AutoInsightEntity } from "@/utils/autoInsight";
import type { BangJoAutoInsightReply, BangJoAutoInsightRequest } from "@/types";

const controller = createAutoInsight<BangJoAutoInsightReply>({
    loader: (entity) => {
        const request: BangJoAutoInsightRequest = entity.type === "segment"
            ? { road_segment_id: String(entity.id) }
            : entity.type === "hex"
                ? { hex_id: Number(entity.id) }
                : { stop_id: String(entity.id) };
        return fetchBangJoAutoInsight(request);
    },
});

export function useAutoInsight(entity: AutoInsightEntity) {
    const key = entityKey(entity);
    const [result, setResult] = useState<{ key: string; value: BangJoAutoInsightReply | null } | null>(null);

    useEffect(() => {
        let active = true;
        controller.schedule(entity).then((value) => {
            if (active) setResult({ key, value });
        });
        return () => {
            active = false;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [key]);

    return { reply: result?.key === key ? result.value : null, loading: result?.key !== key };
}
