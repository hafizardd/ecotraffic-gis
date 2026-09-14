import test from 'node:test';
import assert from 'node:assert/strict';

process.env.NEXT_PUBLIC_TELEMETRY_ENABLED = 'true';
process.env.NEXT_PUBLIC_TELEMETRY_SAMPLE_RATE = '1';
process.env.NEXT_PUBLIC_API_URL = 'https://api.example';
globalThis.window = {};
const { observedFetch, flushTelemetry, reportTelemetry, telemetryRoute } = await import('../src/services/telemetry.ts');

test('fetch preserves response and reports body duration without private URL data', async () => {
    const sent = [];
    globalThis.fetch = async (url, init) => {
        if (url.endsWith('/api/telemetry')) { sent.push(JSON.parse(init.body)); return new Response(null, { status: 204 }); }
        return new Response(JSON.stringify({ result: 42 }), { headers: { 'Content-Type': 'application/json' } });
    };
    const response = await observedFetch('https://api.example/api/cameras/private-id?token=secret');
    assert.deepEqual(await response.json(), { result: 42 });
    assert.equal(response.bodyUsed, true);
    flushTelemetry();
    assert.deepEqual(sent[0].events.map(e => e.name), ['fetch_headers', 'fetch_body']);
    assert.equal(sent[0].events[1].route, 'cameras');
    assert.ok(!JSON.stringify(sent).includes('secret'));
    assert.equal(telemetryRoute('/api/unknown/user-123'), 'other');
});

test('aborted requests preserve exception identity', async () => {
    const sent = [];
    const controller = new AbortController(); controller.abort();
    const failure = new DOMException('aborted', 'AbortError');
    globalThis.fetch = async (url, init) => {
        if (url.endsWith('/api/telemetry')) { sent.push(JSON.parse(init.body)); return new Response(null, { status: 204 }); }
        throw failure;
    };
    await assert.rejects(observedFetch('/api/cameras', { signal: controller.signal }), error => error === failure);
    flushTelemetry();
    assert.equal(sent[0].events[0].outcome, 'aborted');
});

test('bounded telemetry queue and transport failure never throw', async () => {
    let body;
    globalThis.fetch = async (url, init) => { body = JSON.parse(init.body); throw new Error('offline'); };
    for (let i = 0; i < 100; i++) reportTelemetry('js_error', 'page', 'error');
    flushTelemetry();
    assert.equal(body.events.length, 20);
    await new Promise(resolve => setImmediate(resolve));
});
