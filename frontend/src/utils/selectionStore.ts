type Listener = (id: string | null) => void;

let selectedSegmentId: string | null = null;
const listeners = new Set<Listener>();

export function setSelectedSegmentId(id: string | null) {
    selectedSegmentId = id;
    listeners.forEach((listener) => listener(id));
}

export function getSelectedSegmentId() {
    return selectedSegmentId;
}
