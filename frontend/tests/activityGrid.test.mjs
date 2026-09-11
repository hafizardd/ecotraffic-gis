import test from "node:test";
import assert from "node:assert/strict";
import { gridLod, sliderIndex } from "../src/utils/activityGrid.ts";

test("lod switches to coarse below the breakpoint", () => {
    assert.equal(gridLod(12), "coarse");
    assert.equal(gridLod(13), "native");
    assert.equal(gridLod(16), "native");
});

test("slider is hidden with no hours and clamps to the available range", () => {
    assert.equal(sliderIndex([], null), -1);
    const hours = ["2026-09-10T11:00:00+00:00", "2026-09-10T12:00:00+00:00"];
    assert.equal(sliderIndex(hours, null), 1);
    assert.equal(sliderIndex(hours, hours[0]), 0);
    assert.equal(sliderIndex(hours, "2026-09-09T00:00:00+00:00"), 1);
});
