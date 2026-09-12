import test from "node:test";
import assert from "node:assert/strict";
import { cameraDisplayValue } from "../src/utils/cameraValue.ts";

test("live CO2 value always wins over historical", () => {
    const live = { total_co2_g_per_min: 600, freshness_status: "fresh" };
    const historical = { emissions_g_per_min: { co2: 900 }, observed_at: "2026-09-10T07:00:00Z", is_interpolated: true };
    const value = cameraDisplayValue(live, historical);
    assert.equal(value.historical, false);
    assert.equal(value.co2_g_per_min, 600);
    assert.equal(value.is_interpolated, false);
});

test("historical segment value flags itself and carries interpolation", () => {
    const historical = { emissions_g_per_min: { co2: 900 }, observed_at: "2026-09-10T07:00:00Z", is_interpolated: true };
    const value = cameraDisplayValue(undefined, historical);
    assert.equal(value.historical, true);
    assert.equal(value.co2_g_per_min, 900);
    assert.equal(value.observed_at, "2026-09-10T07:00:00Z");
    assert.equal(value.is_interpolated, true);
});

test("no live or historical value stays unavailable", () => {
    const value = cameraDisplayValue(undefined, undefined);
    assert.equal(value.co2_g_per_min, null);
    assert.equal(value.historical, false);
});
