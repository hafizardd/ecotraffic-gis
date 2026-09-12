import test from "node:test";
import assert from "node:assert/strict";
import { haversineKm, neighborEstimate } from "../src/utils/cameraEstimate.ts";

const cam = (camera_id, name, lon, lat) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [lon, lat] },
    properties: { camera_id, name },
});

test("haversine is zero for the same point and positive across a span", () => {
    assert.equal(haversineKm([110.36, -7.79], [110.36, -7.79]), 0);
    assert.ok(haversineKm([110.36, -7.79], [110.46, -7.79]) > 10);
});

test("estimate comes from the nearest camera with data, skipping the target", () => {
    const target = cam("target", "Target", 110.36, -7.79);
    const near = cam("near", "Near", 110.361, -7.79);
    const far = cam("far", "Far", 110.5, -7.79);
    const emissionMap = new Map([["far", { total_co2_g_per_min: 900 }]]);
    const estimate = neighborEstimate(target, [target, near, far], emissionMap, new Map());
    assert.equal(estimate?.cameraId, "far");
    assert.equal(estimate?.emission?.total_co2_g_per_min, 900);
});

test("no candidate data yields null instead of a fabricated number", () => {
    const target = cam("target", "Target", 110.36, -7.79);
    assert.equal(neighborEstimate(target, [target], new Map(), new Map()), null);
});
