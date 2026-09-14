type Name = 'fetch_headers' | 'fetch_body' | 'video_load_event' | 'video_error' | 'video_loading_timeout' | 'page_load' | 'js_error' | 'unhandled_rejection';
type Route = 'cameras' | 'segments' | 'emissions' | 'spatial' | 'analytics' | 'chat' | 'other' | 'page' | 'video';
type Outcome = 'ok' | 'error' | 'aborted' | 'timeout';
type Event = { name: Name; route: Route; outcome: Outcome; duration_ms: number };
const queue: Event[] = [];
let timer: ReturnType<typeof setTimeout> | undefined;
let sampled: boolean | undefined;

function enabled() {
    if (typeof window === 'undefined' || process.env.NEXT_PUBLIC_TELEMETRY_ENABLED !== 'true') return false;
    if (sampled === undefined) {
        const configured = Number(process.env.NEXT_PUBLIC_TELEMETRY_SAMPLE_RATE ?? '0.1');
        sampled = Math.random() < (Number.isFinite(configured) ? Math.max(0, Math.min(1, configured)) : 0.1);
    }
    return sampled;
}

export function flushTelemetry() {
    if (timer) clearTimeout(timer);
    timer = undefined;
    if (!queue.length) return;
    const body = JSON.stringify({ events: queue.splice(0, 20) });
    // No credentials and no retries: diagnostics must not interfere with user requests.
    void fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/telemetry`, {
        method: 'POST', headers: { 'Content-Type': 'text/plain' }, body,
        credentials: 'omit', keepalive: true,
    }).catch(() => {});
}

export function reportTelemetry(name: Name, route: Route, outcome: Outcome, durationMs = 0) {
    if (!enabled() || !Number.isFinite(durationMs)) return;
    // Drop excess events rather than increase traffic during an incident.
    if (queue.length >= 20) return;
    queue.push({ name, route, outcome, duration_ms: Math.min(3600000, Math.max(0, durationMs)) });
    timer ??= setTimeout(flushTelemetry, 5000);
}

export function telemetryRoute(input: string): Route {
    try {
        const path = new URL(input, 'http://local').pathname;
        const group = path.split('/')[2];
        return ['cameras', 'segments', 'emissions', 'spatial', 'analytics', 'chat'].includes(group) ? group as Route : 'other';
    } catch { return 'other'; }
}

/** Keep native Response/stream semantics; time body consumption without cloning large exports. */
export async function observedFetch(input: string, init?: RequestInit): Promise<Response> {
    if (!enabled()) return fetch(input, init);
    const started = performance.now();
    const route = telemetryRoute(input);
    try {
        const response = await fetch(input, init);
        reportTelemetry('fetch_headers', route, response.ok ? 'ok' : 'error', performance.now() - started);
        for (const method of ['json', 'text', 'blob'] as const) {
            const consume = response[method].bind(response);
            Object.defineProperty(response, method, { value: async () => {
                try {
                    const result = await consume();
                    reportTelemetry('fetch_body', route, response.ok ? 'ok' : 'error', performance.now() - started);
                    return result;
                } catch (error) {
                    reportTelemetry('fetch_body', route, init?.signal?.aborted ? 'aborted' : 'error', performance.now() - started);
                    throw error;
                }
            }});
        }
        return response;
    } catch (error) {
        reportTelemetry('fetch_headers', route, init?.signal?.aborted ? 'aborted' : 'error', performance.now() - started);
        throw error;
    }
}
