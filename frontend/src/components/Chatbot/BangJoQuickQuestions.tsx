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
        <div className="flex flex-col gap-[7px]">
            <span className="text-[9px] font-extrabold tracking-[0.12em] text-[#cbd5e1]">PERTANYAAN CEPAT</span>
            {QUESTIONS.map((question) => (
                <button
                    key={question}
                    type="button"
                    className={`${ANALYTICS_BUTTON_CLASS} w-full text-left text-[11px] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--green)]`}
                    onClick={() => onSelect(question)}
                >
                    {question}
                </button>
            ))}
        </div>
    );
}
