export interface SelectionState {
    segmentId: string | null;
    hexId: number | null;
    stopId: string | null;
    cameraId: string | null;
    // Active activity-grid filters, so Bang Jo can answer for what is displayed.
    activityHour: string | null;
    profileDay: string | null;
    isPanelOpen: boolean;
}

type SelectionListener = (state: SelectionState) => void;

const EMPTY: SelectionState = {
    segmentId: null, hexId: null, stopId: null, cameraId: null,
    activityHour: null, profileDay: null, isPanelOpen: false,
};

let selection: SelectionState = { ...EMPTY };
const listeners = new Set<SelectionListener>();

export function setSelection(next: Partial<SelectionState>) {
    const merged = { ...selection, ...next };
    merged.isPanelOpen = next.isPanelOpen
        ?? Boolean(merged.segmentId || merged.hexId != null || merged.stopId || merged.cameraId);
    selection = merged;
    listeners.forEach((listener) => listener(selection));
}

export function getSelection(): SelectionState {
    return selection;
}

export function subscribeSelection(listener: SelectionListener) {
    listeners.add(listener);
    listener(selection);
    return () => {
        listeners.delete(listener);
    };
}

// Chat promotion bus: a panel can hand a question to the open Bang Jo widget.
const questionListeners = new Set<(question: string) => void>();

export function askBangJo(question: string) {
    questionListeners.forEach((listener) => listener(question));
}

export function subscribeBangJoQuestion(listener: (question: string) => void) {
    questionListeners.add(listener);
    return () => {
        questionListeners.delete(listener);
    };
}
