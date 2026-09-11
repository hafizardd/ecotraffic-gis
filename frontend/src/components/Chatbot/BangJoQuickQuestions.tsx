"use client";

const QUESTIONS = [
    "Apa prioritas intervensi untuk koridor ini?",
    "Kenapa skor koridor ini tinggi?",
    "Apakah cakupan halte sudah cukup?",
    "Rekomendasi ASI apa yang cocok?",
];

export default function BangJoQuickQuestions({ onSelect }: { onSelect: (text: string) => void }) {
    return (
        <div className="bangjo-quick">
            <span className="bangjo-quick-label">PERTANYAAN CEPAT</span>
            {QUESTIONS.map((question) => (
                <button
                    key={question}
                    type="button"
                    className="analytics-button bangjo-chip"
                    onClick={() => onSelect(question)}
                >
                    {question}
                </button>
            ))}
        </div>
    );
}
