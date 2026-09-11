import test from "node:test";
import assert from "node:assert/strict";
import { gridLod, nextGridLod, sliderIndex } from "../src/utils/activityGrid.ts";
import { breaksToLabels, breaksToStops } from "../src/constants/mapColors.ts";

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

test("choropleth labels round each break for the legend", () => {
    assert.deepEqual(breaksToLabels([1.234, 25.6, 50, 75.4, 100]), ["1.2", "26", "50", "75", "100"]);
    assert.equal(breaksToLabels(null), null);
});

test("slider is hidden with no hours and clamps to the available range", () => {
    assert.equal(sliderIndex([], null), -1);
    const hours = ["2026-09-10T11:00:00+00:00", "2026-09-10T12:00:00+00:00"];
    assert.equal(sliderIndex(hours, null), 1);
    assert.equal(sliderIndex(hours, hours[0]), 0);
    assert.equal(sliderIndex(hours, "2026-09-09T00:00:00+00:00"), 1);
});
