import test from "node:test";
import assert from "node:assert/strict";
import { circlePolygon } from "../src/utils/geo.ts";

function metersBetween([lon1, lat1], [lon2, lat2]) {
    const toRad = (v) => (v * Math.PI) / 180;
    const R = 6378137;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
}

test("circle polygon is closed with one vertex per step", () => {
    const ring = circlePolygon([110.37, -7.79], 500, 32).coordinates[0];
    assert.equal(ring.length, 33);
    assert.deepEqual(ring[0], ring[ring.length - 1]);
});

test("every vertex sits ~500 m from the centre", () => {
    const center = [110.37, -7.79];
    const ring = circlePolygon(center, 500, 64).coordinates[0];
    for (const vertex of ring) {
        const distance = metersBetween(center, vertex);
        assert.ok(Math.abs(distance - 500) < 1, `expected ~500m, got ${distance.toFixed(2)}`);
    }
});
