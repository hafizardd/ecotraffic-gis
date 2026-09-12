import test from "node:test";
import assert from "node:assert/strict";
import { bangjoDock, BANGJO_DEFAULT_RIGHT_PX } from "../src/utils/bangjoLayout.ts";

test("panel open on a wide viewport docks left of the data panel", () => {
    const dock = bangjoDock({ isPanelOpen: true, viewportWidth: 1440, panelWidth: 430 });
    assert.equal(dock.docked, true);
    assert.equal(dock.offsetRight, 430 + 34);
    assert.equal(dock.hideFab, false);
});

test("panel closed uses the default corner offset", () => {
    const dock = bangjoDock({ isPanelOpen: false, viewportWidth: 1440, panelWidth: 430 });
    assert.equal(dock.docked, false);
    assert.equal(dock.offsetRight, BANGJO_DEFAULT_RIGHT_PX);
    assert.equal(dock.hideFab, false);
});

test("narrow viewport with panel open hides the FAB", () => {
    const dock = bangjoDock({ isPanelOpen: true, viewportWidth: 700, panelWidth: 430 });
    assert.equal(dock.docked, false);
    assert.equal(dock.hideFab, true);
    assert.equal(dock.offsetRight, BANGJO_DEFAULT_RIGHT_PX);
});

test("narrow viewport without a panel keeps the FAB", () => {
    const dock = bangjoDock({ isPanelOpen: false, viewportWidth: 700, panelWidth: 430 });
    assert.equal(dock.hideFab, false);
});
