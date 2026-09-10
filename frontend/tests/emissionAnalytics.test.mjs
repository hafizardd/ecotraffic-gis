import test from "node:test";
import assert from "node:assert/strict";
import { analyticsQuery, analyticsLiveStatus, isNewerSegment, validRealtimeSegment } from "../src/utils/emissionAnalytics.ts";

const now = "2026-09-10T12:00:00.000Z";
const filter = { timeRange: "1h", segmentId: "A", corridorId: "C", from: null, to: null };

test("all visual queries preserve the same period and both location filters", () => {
    for (const hours of [1, 3, 12, 24]) {
        const query = analyticsQuery({ ...filter, timeRange: `${hours}h` }, now);
        assert.equal(Date.parse(query.to) - Date.parse(query.from), hours * 3600000);
        assert.equal(query.segment_id, "A");
        assert.equal(query.corridor_id, "C");
    }
});

test("custom history/export range does not move when new live data arrives", () => {
    const fixed = { ...filter, from: "2026-09-09T00:00:00.000Z", to: "2026-09-10T00:00:00.000Z" };
    assert.deepEqual(analyticsQuery(fixed, now), analyticsQuery(fixed, "2026-09-11T00:00:00.000Z"));
});

test("late processing cannot overwrite a newer observation", () => {
    const latest = { observed_at: now, processed_at: now };
    assert.equal(isNewerSegment({ observed_at: "2026-09-10T11:59:00Z", processed_at: "2026-09-10T13:00:00Z" }, latest), false);
    assert.equal(isNewerSegment({ observed_at: now, processed_at: "2026-09-10T12:01:00Z" }, latest), true);
    assert.equal(isNewerSegment({ observed_at: "invalid", processed_at: now }, latest), false);
});

test("freshness ages without receiving another WebSocket update", () => {
    assert.equal(analyticsLiveStatus(now, 180, "LIVE", Date.parse(now) + 4000), "LIVE");
    assert.equal(analyticsLiveStatus(now, 180, "LIVE", Date.parse(now) + 181000), "STALE");
    assert.equal(analyticsLiveStatus(now, 180, "HISTORICAL", Date.parse(now)), "HISTORICAL");
    assert.equal(analyticsLiveStatus(null, 180, "LIVE", Date.parse(now)), "NO DATA");
});

test("all eight zero pollutants are valid; missing/nonfinite payloads are rejected", () => {
    const row = { segment_id: "A", corridor_id: "C", observed_at: now, processed_at: now,
        emissions_kg_h: { tsp: 0, co: 0, nox: 0, so2: 0, hc: 0, co2: 0, ch4: 0, n2o: 0 } };
    assert.equal(validRealtimeSegment(row), true);
    assert.equal(validRealtimeSegment({ ...row, emissions_kg_h: { co2: 1 } }), false);
    assert.equal(validRealtimeSegment({ ...row, emissions_kg_h: { ...row.emissions_kg_h, co2: Infinity } }), false);
    assert.equal(validRealtimeSegment(null), false);
});
