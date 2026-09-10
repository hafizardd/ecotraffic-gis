"use client";

export default function BangJoFab({ onOpen }: { onOpen: () => void }) {
    return (
        <button
            type="button"
            className="bangjo-fab"
            aria-label="Buka asisten Bang Jo"
            aria-expanded={false}
            onClick={onOpen}
        >
            <span className="bangjo-fab-mark" aria-hidden="true"><i /><i /><i /></span>
            <span className="bangjo-fab-status" aria-hidden="true" />
        </button>
    );
}
