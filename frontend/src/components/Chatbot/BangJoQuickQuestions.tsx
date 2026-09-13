"use client";
import { ANALYTICS_BUTTON_CLASS } from "@/styles/tailwind";

export type QuickQuestionTarget = "segment" | "hex" | "stop" | null;

// Prompts match the object the user has selected, so "ini" always has a
// referent. With nothing selected the prompts stay non-referential.
const QUESTIONS: Record<"segment" | "hex" | "stop" | "none", string[]> = {
    segment: [
        "Apa prioritas intervensi untuk koridor ini?",
        "Kenapa skor koridor ini tinggi?",
        "Apakah cakupan halte sudah cukup?",
        "Rekomendasi ASI apa yang cocok?",
    ],
    hex: [
        "Apa prioritas intervensi untuk sel ini?",
        "Kenapa potensi sel ini tinggi?",
        "Koridor apa yang melintasi sel ini?",
        "Rekomendasi ASI apa yang cocok?",
    ],
    stop: [
        "Bagaimana kualitas halte ini?",
        "Apakah halte ini perlu diperbaiki?",
        "Apakah cakupan halte di sekitar sini cukup?",
        "Rekomendasi ASI apa yang cocok?",
    ],
    none: [
        "Daerah mana dengan potensi aktivitas tertinggi?",
        "Koridor mana yang paling perlu intervensi?",
        "Halte mana yang paling buruk?",
        "Bagaimana sebaran emisi koridor?",
    ],
};

export default function BangJoQuickQuestions({ target, onSelect }: {
    target: QuickQuestionTarget;
    onSelect: (text: string) => void;
}) {
    const questions = QUESTIONS[target ?? "none"];
    return (
        <div className="flex flex-col gap-2">
            <span className="text-[9px] font-bold tracking-[0.11em] text-(--muted) uppercase">Pertanyaan cepat</span>
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
