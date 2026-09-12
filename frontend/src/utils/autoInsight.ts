// Pure debounce + per-entity cache for auto-insight requests. No React/DOM so
// it is unit-testable in the existing Node harness and reusable from hooks.
export type AutoInsightEntityType = "segment" | "hex" | "stop";

export interface AutoInsightEntity {
    type: AutoInsightEntityType;
    id: string | number;
    // Active grid hour (ISO) + display label; part of the cache key so scrubbing
    // the hour slider regenerates an insight that matches the displayed hour.
    hour?: string | null;
    hourLabel?: string | null;
}

export interface AutoInsightOptions<T> {
    loader: (entity: AutoInsightEntity) => Promise<T>;
    debounceMs?: number;
    ttlMs?: number;
    now?: () => number;
}

export function entityKey(entity: AutoInsightEntity): string {
    const base = `${entity.type}:${entity.id}`;
    return entity.hour ? `${base}:${entity.hour}` : base;
}

export function createAutoInsight<T>({
    loader,
    debounceMs = 400,
    ttlMs = 300_000,
    now = Date.now,
}: AutoInsightOptions<T>) {
    const cache = new Map<string, { value: T; at: number }>();
    let timer: ReturnType<typeof setTimeout> | null = null;
    let pending: { entity: AutoInsightEntity; waiters: ((value: T | null) => void)[] } | null = null;

    function flush() {
        timer = null;
        const current = pending;
        pending = null;
        if (!current) return;
        const key = entityKey(current.entity);
        const cached = cache.get(key);
        if (cached && now() - cached.at < ttlMs) {
            current.waiters.forEach((resolve) => resolve(cached.value));
            return;
        }
        loader(current.entity)
            .then((value) => {
                cache.set(key, { value, at: now() });
                current.waiters.forEach((resolve) => resolve(value));
            })
            .catch(() => current.waiters.forEach((resolve) => resolve(null)));
    }

    function schedule(entity: AutoInsightEntity): Promise<T | null> {
        return new Promise((resolve) => {
            const key = entityKey(entity);
            const cached = cache.get(key);
            if (cached && now() - cached.at < ttlMs) {
                resolve(cached.value);
                return;
            }
            if (pending && entityKey(pending.entity) === key) {
                pending.waiters.push(resolve);
                return;
            }
            // A different entity arrived before the debounce fired: supersede it.
            if (pending) pending.waiters.forEach((resolve) => resolve(null));
            pending = { entity, waiters: [resolve] };
            if (timer) clearTimeout(timer);
            timer = setTimeout(flush, debounceMs);
        });
    }

    function cancel() {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
        if (pending) {
            pending.waiters.forEach((resolve) => resolve(null));
            pending = null;
        }
    }

    function clearCache() {
        cache.clear();
    }

    return { schedule, cancel, clearCache };
}
