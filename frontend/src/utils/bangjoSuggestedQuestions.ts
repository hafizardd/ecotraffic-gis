// Initial "suggested questions" for an empty Bang Jo conversation. Pure logic so
// it can be unit-tested without rendering: one meta question, one tied to the
// live/replay lens, and one tied to the current map selection (falling back to a
// generic corridor question when nothing is selected).

export type SuggestedTarget = "segment" | "hex" | "stop" | null;
export type SuggestedTimeMode = "live" | "replay";

export interface SuggestedContext {
    target: SuggestedTarget;
    timeMode: SuggestedTimeMode;
}

const META_QUESTION = "Apa itu EcoTraffic dan bagaimana cara membacanya?";

const SELECTION_QUESTION: Record<"segment" | "hex" | "stop" | "none", string> = {
    segment: "Apa prioritas intervensi untuk koridor ini?",
    hex: "Apa prioritas intervensi untuk sel ini?",
    stop: "Bagaimana kualitas halte ini?",
    none: "Koridor mana yang emisinya paling tinggi?",
};

function modeQuestion(timeMode: SuggestedTimeMode): string {
    return timeMode === "live"
        ? "Daerah mana yang paling ramai sekarang?"
        : "Jam segini biasanya paling padat di mana?";
}

export function suggestedQuestions({ target, timeMode }: SuggestedContext): string[] {
    return [META_QUESTION, modeQuestion(timeMode), SELECTION_QUESTION[target ?? "none"]];
}
