"use client";
import { ANALYTICS_BUTTON_CLASS } from "@/styles/tailwind";

const QUESTIONS = [
    "Apa prioritas intervensi untuk koridor ini?",
    "Kenapa skor koridor ini tinggi?",
    "Apakah cakupan halte sudah cukup?",
    "Rekomendasi ASI apa yang cocok?",
];

export default function BangJoQuickQuestions({ onSelect }: { onSelect: (text: string) => void }) {
    return (
        <div className="flex flex-col gap-2">
            <span className="text-[9px] font-bold tracking-[0.11em] text-(--muted) uppercase">Pertanyaan cepat</span>
            {QUESTIONS.map((question) => (
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
