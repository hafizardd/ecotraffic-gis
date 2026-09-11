import test from "node:test";
import assert from "node:assert/strict";
import { MODE_VISIBILITY, MAP_MODES, isMapMode, interventionColor } from "../src/constants/mapColors.ts";

test("each map mode exposes exactly its own thematic layers", () => {
    assert.deepEqual(MODE_VISIBILITY.traffic, { cameras: true, segments: true, surveyStops: false, activityGrid: false });
    assert.deepEqual(MODE_VISIBILITY.potential, { cameras: false, segments: false, surveyStops: true, activityGrid: true });
});

test("mode list and guard stay in sync with the combined view", () => {
    assert.deepEqual(MAP_MODES.map((mode) => mode.key), ["traffic", "potential"]);
    assert.equal(isMapMode("potential"), true);
    assert.equal(isMapMode("bus"), false);
    assert.equal(isMapMode("nope"), false);
    assert.equal(isMapMode(null), false);
});

function channels(hex) {
    return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
}

test("bus stop colour goes red (low score) to green (high score)", () => {
    const low = channels(interventionColor(0));
    const high = channels(interventionColor(100));
    assert.ok(low[0] > low[1] && low[0] > low[2], `low score should be red-dominant: ${low}`);
    assert.ok(high[1] > high[0] && high[1] > high[2], `high score should be green-dominant: ${high}`);
    assert.notEqual(interventionColor(75), interventionColor(25));
    assert.equal(interventionColor(null), "#94a3b8");
});
