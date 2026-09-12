import test from "node:test";
import assert from "node:assert/strict";
import { gridLod, nextGridLod, sliderIndex, withDay, hourKey, isWholeRegionLod, adjacentTierToPrefetch, featureInBbox, dataStatusLabel, noDataReasonLabel } from "../src/utils/activityGrid.ts";
import { breaksToStops } from "../src/constants/mapColors.ts";

test("lod steps coarse -> medium -> sub -> fine across the zoom breakpoints", () => {
    assert.equal(gridLod(9), "coarse");
    assert.equal(gridLod(10), "medium");
    assert.equal(gridLod(11.9), "medium");
    assert.equal(gridLod(12), "sub");
    assert.equal(gridLod(13.9), "sub");
    assert.equal(gridLod(14), "fine");
    assert.equal(gridLod(16), "fine");
});

test("nextGridLod holds the current tier inside the hysteresis band", () => {
    assert.equal(nextGridLod(14.4, "sub"), "sub");
    assert.equal(nextGridLod(14.6, "sub"), "fine");
    assert.equal(nextGridLod(13.4, "fine"), "sub");
    assert.equal(nextGridLod(9.6, "medium"), "medium");
    assert.equal(nextGridLod(9.4, "medium"), "coarse");
    assert.equal(nextGridLod(12.6, "medium"), "sub");
    assert.equal(nextGridLod(16, "coarse"), "fine");
    assert.equal(nextGridLod(9, "fine"), "coarse");
});

test("choropleth stops map quantile breaks onto the five tier colours", () => {
    const stops = breaksToStops([1, 25, 50, 75, 100]);
    assert.equal(stops.length, 10);
    assert.deepEqual(stops.slice(0, 2), [1, "#bbf7d0"]);
    assert.deepEqual(stops.slice(-2), [100, "#ef4444"]);
    assert.equal(breaksToStops(null), null);
    assert.equal(breaksToStops([5]), null);
});

test("slider is hidden with no hours and clamps to the available range", () => {
    assert.equal(sliderIndex([], null), -1);
    const hours = ["2026-09-10T11:00:00+00:00", "2026-09-10T12:00:00+00:00"];
    assert.equal(sliderIndex(hours, null), 1);
    assert.equal(sliderIndex(hours, hours[0]), 0);
    assert.equal(sliderIndex(hours, "2026-09-09T00:00:00+00:00"), 1);
});

test("withDay reuses a profile hour on any calendar day", () => {
    assert.equal(withDay("2026-09-10T07:00:00.000Z", "2026-09-05"), "2026-09-05T07:00:00.000Z");
    assert.equal(withDay("2026-09-10T20:00:00.000Z", "2026-09-05"), "2026-09-05T20:00:00.000Z");
    // No day selected keeps the canonical profile hour untouched.
    assert.equal(withDay("2026-09-10T07:00:00.000Z", null), "2026-09-10T07:00:00.000Z");
});

test("hourKey ignores the date so a day switch is a cache hit", () => {
    assert.equal(hourKey("2026-09-10T07:00:00.000Z"), "07:00");
    assert.equal(hourKey("2026-09-05T07:00:00.000Z"), "07:00");
    assert.equal(hourKey(null), "");
});

test("aggregated tiers are region-wide, native fine is viewport-scoped", () => {
    assert.equal(isWholeRegionLod("coarse"), true);
    assert.equal(isWholeRegionLod("medium"), true);
    assert.equal(isWholeRegionLod("sub"), true);
    assert.equal(isWholeRegionLod("fine"), false);
});

test("adjacent tier prefetch only warms the far side of a nearby boundary", () => {
    assert.equal(adjacentTierToPrefetch(10.4, "coarse"), "medium");
    assert.equal(adjacentTierToPrefetch(10.4, "medium"), "coarse");
    assert.equal(adjacentTierToPrefetch(13.6, "sub"), "fine");
    assert.equal(adjacentTierToPrefetch(11.0, "medium"), null);
    assert.equal(adjacentTierToPrefetch(16.0, "fine"), null);
});

test("featureInBbox tests polygon vertices against the viewport", () => {
    const polygon = { geometry: { coordinates: [[[110.0, -7.0], [110.1, -7.0], [110.1, -7.1]]] } };
    assert.equal(featureInBbox(polygon, "109.9,-7.2,110.2,-6.9"), true);
    assert.equal(featureInBbox(polygon, "0,0,1,1"), false);
    assert.equal(featureInBbox(polygon, null), true);
});

test("data status and no-data reasons carry user-facing labels", () => {
    assert.equal(dataStatusLabel("live"), "Terukur");
    assert.equal(dataStatusLabel("fallback"), "Perkiraan area terdekat");
    assert.equal(dataStatusLabel("static"), "Data statis");
    assert.equal(dataStatusLabel(null), "Tidak tersedia");
    assert.equal(noDataReasonLabel("no_mapped_segment"), "Tidak ada segmen jalan yang memotong sel ini.");
    assert.equal(noDataReasonLabel("mapped_but_no_volume"), "Ada segmen jalan, tetapi tidak ada sampel volume pada jam ini.");
    assert.equal(noDataReasonLabel(null), null);
});
