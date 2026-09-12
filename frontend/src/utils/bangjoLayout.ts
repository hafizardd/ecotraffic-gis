// Pure dock geometry for the Bang Jo panel/FAB. Kept dependency-free so it can
// be covered by the Node test harness without a DOM.
export const BANGJO_NARROW_BREAKPOINT = 760;
export const BANGJO_GAP_PX = 34;
export const BANGJO_DEFAULT_RIGHT_PX = 22;

export interface BangjoDockInput {
    isPanelOpen: boolean;
    viewportWidth: number;
    panelWidth: number;
    narrowBreakpoint?: number;
}

export interface BangjoDock {
    // Distance from the right edge for the fixed panel/FAB.
    offsetRight: number;
    // True when the widget sits beside an open data panel (not full-width narrow).
    docked: boolean;
    // On narrow viewports an open data panel covers the map; hide the FAB.
    hideFab: boolean;
}

export function bangjoDock({
    isPanelOpen,
    viewportWidth,
    panelWidth,
    narrowBreakpoint = BANGJO_NARROW_BREAKPOINT,
}: BangjoDockInput): BangjoDock {
    const narrow = viewportWidth <= narrowBreakpoint;
    const docked = isPanelOpen && !narrow;
    const offsetRight = docked ? panelWidth + BANGJO_GAP_PX : BANGJO_DEFAULT_RIGHT_PX;
    const hideFab = isPanelOpen && narrow;
    return { offsetRight, docked, hideFab };
}
