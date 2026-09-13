"use client";

import { useEffect, useRef, useState } from "react";
import useBangJoChat from "@/hooks/useBangJoChat";
import BangJoFab from "./BangJoFab";
import BangJoPanel from "./BangJoPanel";
import type { QuickQuestionTarget } from "./BangJoQuickQuestions";
import { subscribeBangJoQuestion, subscribeSelection, type SelectionState } from "@/utils/selectionStore";
import { bangjoDock } from "@/utils/bangjoLayout";

// Matches --data-panel-width: min(430px, 35vw) in globals.css.
const DATA_PANEL_MAX_PX = 430;

export default function BangJoWidget() {
    const [open, setOpen] = useState(false);
    const [minimized, setMinimized] = useState(false);
    const [selection, setSelectionState] = useState<SelectionState | null>(null);
    const fabRef = useRef<HTMLButtonElement>(null);
    const { messages, isTyping, sendMessage } = useBangJoChat();
    // Prompts follow the selected object so a referential template ("ini") always
    // points at something the user has actually picked.
    const quickTarget: QuickQuestionTarget = selection?.segmentId
        ? "segment"
        : selection?.stopId
            ? "stop"
            : selection?.hexId != null
                ? "hex"
                : null;

    useEffect(() => subscribeSelection(setSelectionState), []);

    useEffect(
        () => subscribeBangJoQuestion((question) => {
            setOpen(true);
            setMinimized(false);
            sendMessage(question);
        }),
        [sendMessage],
    );

    // Dock the widget beside an open data panel (root-cause fix for the
    // FAB/panel overlap) and hide the FAB on narrow viewports.
    useEffect(() => {
        const viewportWidth = window.innerWidth;
        const panelWidth = Math.min(DATA_PANEL_MAX_PX, viewportWidth * 0.35);
        const dock = bangjoDock({ isPanelOpen: Boolean(selection?.isPanelOpen), viewportWidth, panelWidth });
        const root = document.documentElement;
        root.setAttribute("data-data-panel", dock.docked ? "open" : "closed");
        root.setAttribute("data-bangjo-fab", dock.hideFab ? "hidden" : "shown");
        root.style.setProperty("--bangjo-offset-right", `${dock.offsetRight}px`);
    }, [selection?.isPanelOpen]);

    return (
        <>
            {!open && <BangJoFab buttonRef={fabRef} onOpen={() => { setOpen(true); setMinimized(false); }} />}
            {open && (
                <BangJoPanel
                    messages={messages}
                    isTyping={isTyping}
                    minimized={minimized}
                    quickTarget={quickTarget}
                    onSend={sendMessage}
                    onMinimize={() => setMinimized((value) => !value)}
                    onClose={() => {
                        setOpen(false);
                        setMinimized(false);
                        window.requestAnimationFrame(() => fabRef.current?.focus());
                    }}
                />
            )}
        </>
    );
}
