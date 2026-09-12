import { useRef, useState } from "react";
import { fetchBangJoReply } from "@/services/api";
import { getSelection } from "@/utils/selectionStore";
import { fmtDateTimeId } from "@/utils/format";
import { BangJoMessage } from "@/types";

function newId() {
    return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function formatAnswer(reply: Awaited<ReturnType<typeof fetchBangJoReply>>): string {
    if (reply.blocked) {
        return reply.message ?? "Maaf, pertanyaan ini di luar cakupan yang bisa saya bantu.";
    }
    if (reply.answer?.content) {
        return reply.answer.content;
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
        // Keep the history short; the backend budget trims further if needed.
        const history = messagesRef.current.slice(-4).map((message) => ({ role: message.role, content: message.content }));
        setMessages((prev) => [...prev, { id: newId(), role: "user", content, timestamp: new Date().toISOString() }]);
        setIsTyping(true);
        const selection = getSelection();
        const hour = selection.activityHour;
        try {
            const reply = await fetchBangJoReply(content, {
                road_segment_id: selection.segmentId,
                hex_id: selection.hexId,
                stop_id: selection.stopId,
                hour,
                hour_label: hour ? fmtDateTimeId(hour) : null,
            }, history);
            setMessages((prev) => [...prev, {
                id: newId(), role: "assistant", content: formatAnswer(reply),
                citations: reply.answer?.citations,
                contextLabel: reply.context_label ?? undefined,
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
