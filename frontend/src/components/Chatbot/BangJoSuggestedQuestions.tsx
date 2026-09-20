"use client";
import { ANALYTICS_BUTTON_CLASS } from "@/styles/tailwind";
import type { QuickQuestionTarget } from "./BangJoQuickQuestions";
import { suggestedQuestions, type SuggestedTimeMode } from "@/utils/bangjoSuggestedQuestions";

// Shown before the first message, unlike BangJoQuickQuestions which are
// contextual follow-ups shown after an answer.
export default function BangJoSuggestedQuestions({ target, timeMode, onSelect }: {
    target: QuickQuestionTarget;
    timeMode: SuggestedTimeMode;
    onSelect: (text: string) => void;
}) {
    const questions = suggestedQuestions({ target, timeMode });
    return (
        <div className="flex flex-col gap-2">
            <span className="text-[9px] font-bold tracking-[0.11em] text-(--muted) uppercase">Pertanyaan yang disarankan</span>
            {questions.map((question) => (
                <button
                    key={question}
                    type="button"
                    className={`${ANALYTICS_BUTTON_CLASS} w-full text-left text-[11px] leading-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--selection)`}
                    onClick={() => onSelect(question)}
                >
                    {question}
                </button>
            ))}
        </div>
    );
}
