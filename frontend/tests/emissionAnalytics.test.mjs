import test from "node:test";
import assert from "node:assert/strict";
import { analyticsQuery, analyticsLiveStatus, clampPage, filterSelectOptions, isNewerSegment, numberDuplicateNames, pageWindow, validRealtimeSegment } from "../src/utils/emissionAnalytics.ts";

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

test("pagination window keeps first/last and collapses gaps", () => {
    assert.deepEqual(pageWindow(1, 1), [1]);
    assert.deepEqual(pageWindow(1, 5), [1, 2, 3, 4, 5]);
    assert.deepEqual(pageWindow(10, 20), [1, "gap", 8, 9, 10, 11, 12, "gap", 20]);
    assert.deepEqual(pageWindow(1, 20), [1, 2, 3, "gap", 20]);
    assert.deepEqual(pageWindow(20, 20), [1, "gap", 18, 19, 20]);
});

test("history page jump clamps invalid input into range", () => {
    assert.equal(clampPage("5", 10), 5);
    assert.equal(clampPage("", 10), 1);
    assert.equal(clampPage("abc", 10), 1);
    assert.equal(clampPage("0", 10), 1);
    assert.equal(clampPage("-3", 10), 1);
    assert.equal(clampPage("999", 10), 10);
    assert.equal(clampPage("7.9", 10), 7);
    assert.equal(clampPage("4", 1), 1);
    assert.equal(clampPage("2", 0), 1);
});

test("duplicate road names are numbered in order; singletons are untouched", () => {
    assert.deepEqual(numberDuplicateNames(["Jalan Kenari", "Jalan Kenari", "Jalan Kenari"]), ["Jalan Kenari 1", "Jalan Kenari 2", "Jalan Kenari 3"]);
    assert.deepEqual(numberDuplicateNames(["A", "B", "A", "A", "B", "C"]), ["A 1", "B 1", "A 2", "A 3", "B 2", "C"]);
    assert.deepEqual(numberDuplicateNames([]), []);
});

test("select search is case-insensitive and trims the query", () => {
    const options = [{ value: "1", label: "Jalan Kenari 1" }, { value: "2", label: "Jalan Magelang" }, { value: "3", label: "Jalan Veteran" }];
    assert.deepEqual(filterSelectOptions(options, "kenari"), [options[0]]);
    assert.deepEqual(filterSelectOptions(options, "  JALAN  "), options);
    assert.deepEqual(filterSelectOptions(options, ""), options);
    assert.deepEqual(filterSelectOptions(options, "zzz"), []);
});
