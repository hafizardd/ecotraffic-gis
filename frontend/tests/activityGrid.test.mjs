import test from "node:test";
import assert from "node:assert/strict";
import { aggregateCoarseGrid, gridLod, sliderIndex } from "../src/utils/activityGrid.ts";

function feature(hexId, potential, { lon = 110.36, lat = -7.79, area = 1 } = {}) {
    return {
        type: "Feature",
        geometry: {
            type: "Polygon",
            coordinates: [[[lon, lat], [lon + 0.01, lat], [lon + 0.01, lat + 0.01], [lon, lat + 0.01], [lon, lat]]],
        },
        properties: {
            hex_id: hexId, luas_km2: area, poi_total: 0, poi_breakdown: {}, penduduk: 0, volume_mean: 0,
            norm_volume: 1, norm_poi: 1, norm_penduduk: 1, skor_total_ahp: 1, ranking: hexId,
            klasifikasi_potensi: "Sedang", ahp_weight_version: "hex-ahp-v1", source: "test", potential,
        },
    };
}

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

test("coarse lod replaces per-cell tiers with the area-weighted mean", () => {
    const decorated = aggregateCoarseGrid([
        feature(1, 5),
        feature(2, 1, { lon: 110.365, lat: -7.795 }),
    ]);
    assert.deepEqual(decorated.map((f) => f.properties.potential), [3, 3]);
    assert.deepEqual(decorated.map((f) => f.properties.hex_id), [null, null]);
    assert.deepEqual(decorated.map((f) => f.properties.aggregated_count), [2, 2]);
});

test("area weights shift the mean", () => {
    const decorated = aggregateCoarseGrid([feature(1, 5, { area: 3 }), feature(2, 1, { area: 1 })]);
    assert.deepEqual(decorated.map((f) => f.properties.potential), [4, 4]);
});

test("no-data cells are excluded from the mean but still counted", () => {
    const decorated = aggregateCoarseGrid([feature(1, 5), feature(2, 0)]);
    assert.deepEqual(decorated.map((f) => f.properties.potential), [5, 5]);
    assert.deepEqual(decorated.map((f) => f.properties.aggregated_count), [2, 2]);
});
