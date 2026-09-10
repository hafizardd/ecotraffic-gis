"use client";

const QUESTIONS = [
    "Bagaimana kondisi emisi saat ini?",
    "Lokasi mana dengan CO tertinggi?",
    "Tampilkan tren emisi 30 menit terakhir",
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
