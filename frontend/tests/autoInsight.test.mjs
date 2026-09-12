import test from "node:test";
import assert from "node:assert/strict";
import { createAutoInsight, entityKey } from "../src/utils/autoInsight.ts";

test("debounce coalesces rapid selection changes into one request", async () => {
    let calls = 0;
    const controller = createAutoInsight({
        debounceMs: 5,
        loader: async () => {
            calls += 1;
            return { n: calls };
        },
    });

    const first = controller.schedule({ type: "segment", id: "A" });
    const second = controller.schedule({ type: "segment", id: "A" });
    const [a, b] = await Promise.all([first, second]);

    assert.equal(calls, 1);
    assert.deepEqual(a, b);
});

test("cache returns the same entity without a second request", async () => {
    let calls = 0;
    const controller = createAutoInsight({
        debounceMs: 0,
        loader: async () => {
            calls += 1;
            return { n: calls };
        },
    });

    const first = await controller.schedule({ type: "segment", id: "A" });
    const second = await controller.schedule({ type: "segment", id: "A" });

    assert.equal(calls, 1);
    assert.deepEqual(first, second);
});

test("entity switch bypasses the cache", async () => {
    let calls = 0;
    const controller = createAutoInsight({
        debounceMs: 0,
        loader: async () => {
            calls += 1;
            return { n: calls };
        },
    });

    await controller.schedule({ type: "segment", id: "A" });
    await controller.schedule({ type: "segment", id: "B" });

    assert.equal(calls, 2);
});

test("a superseded entity resolves null", async () => {
    const controller = createAutoInsight({ debounceMs: 5, loader: async () => "ok" });

    const first = controller.schedule({ type: "segment", id: "A" });
    controller.schedule({ type: "segment", id: "B" });

    assert.equal(await first, null);
});

test("ttl expiry refetches the same entity", async () => {
    let calls = 0;
    let clock = 0;
    const controller = createAutoInsight({
        debounceMs: 0,
        ttlMs: 100,
        now: () => clock,
        loader: async () => {
            calls += 1;
            return calls;
        },
    });

    await controller.schedule({ type: "hex", id: 1 });
    clock = 50;
    await controller.schedule({ type: "hex", id: 1 });
    assert.equal(calls, 1);

    clock = 200;
    await controller.schedule({ type: "hex", id: 1 });
    assert.equal(calls, 2);
});

test("entityKey is stable", () => {
    assert.equal(entityKey({ type: "hex", id: 7 }), "hex:7");
});
