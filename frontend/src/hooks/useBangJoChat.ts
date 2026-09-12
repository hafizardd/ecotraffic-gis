import { useRef, useState } from "react";
import { fetchBangJoReply } from "@/services/api";
import { getSelectedSegmentId } from "@/utils/selectionStore";
import { BangJoMessage } from "@/types";

function newId() {
    return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function formatAnswer(reply: Awaited<ReturnType<typeof fetchBangJoReply>>): string {
    if (reply.blocked) {
        return reply.message ?? "Maaf, pertanyaan ini di luar cakupan yang bisa saya bantu.";
    }
    if (reply.answer) {
        const answer = reply.answer;
        return [
            answer.summary,
            answer.drivers.length ? `Pendorong: ${answer.drivers.join("; ")}` : "",
            answer.asi_category ? `Kategori ASI: ${answer.asi_category}` : "",
            answer.recommendation,
            answer.evidence.length ? `Bukti: ${answer.evidence.join("; ")}` : "",
        ].filter(Boolean).join("\n\n");
    }
    if (reply.detail) return reply.detail;
    if (reply.candidates?.length) {
        const seen = new Set<string>();
        const names = reply.candidates
            .map((item) => item.name)
            .filter((name) => {
                if (seen.has(name)) return false;
                seen.add(name);
                return true;
            });
        return `Sebutkan nama koridor yang dimaksud, misalnya: ${names.slice(0, 3).join(", ")}.`;
    }
    return "Saya belum bisa menentukan koridor. Pilih segmen di peta lalu tanya lagi.";
}

export default function useBangJoChat() {
    const [messages, setMessages] = useState<BangJoMessage[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const messagesRef = useRef<BangJoMessage[]>([]);
    messagesRef.current = messages;

    const sendMessage = async (text: string) => {
        const content = text.trim();
        if (!content || isTyping) return;
        const history = messagesRef.current.slice(-6).map((message) => ({ role: message.role, content: message.content }));
        setMessages((prev) => [...prev, { id: newId(), role: "user", content, timestamp: new Date().toISOString() }]);
        setIsTyping(true);
        try {
            const reply = await fetchBangJoReply(content, getSelectedSegmentId(), history);
            setMessages((prev) => [...prev, {
                id: newId(), role: "assistant", content: formatAnswer(reply),
                contextLabel: reply.context_label ?? undefined,
                citations: reply.answer?.citations ?? undefined,
                timestamp: new Date().toISOString(),
            }]);
        } catch (error) {
            setMessages((prev) => [...prev, {
                id: newId(), role: "assistant",
                content: error instanceof Error ? `Bang Jo tidak dapat memuat jawaban: ${error.message}` : "Layanan Bang Jo sedang tidak tersedia.",
                timestamp: new Date().toISOString(),
            }]);
        } finally {
            setIsTyping(false);
        }
    };

    return { messages, isTyping, sendMessage };
}
