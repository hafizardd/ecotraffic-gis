import { useEffect, useRef, useState } from "react";
import { BangJoMessage } from "@/types";

const REPLY_DELAY_MS = 900;

function newId() {
    return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function stubReply(text: string): { content: string; contextLabel?: string } {
    const lower = text.toLowerCase();
    if (lower.includes("tren")) {
        return { content: "Tren emisi 30 menit terakhir masih fluktuatif. Puncak CO2 terjadi pada siklus dengan volume kendaraan tertinggi.", contextLabel: "window = 30 menit terakhir" };
    }
    if (lower.includes("tinggi") || lower.includes("tertinggi")) {
        return { content: "Lokasi dengan konsentrasi CO tertinggi saat ini adalah Malioboro DPRD, disusul Simpang Tugu.", contextLabel: "selectedLocation = Malioboro DPRD" };
    }
    return { content: `Baik, saya catat: "${text}". Untuk jawaban berbasis data, saya akan membaca metrik dashboard yang tersedia.`, contextLabel: "selectedLocation = Malioboro DPRD" };
}

export default function useBangJoChat() {
    const [messages, setMessages] = useState<BangJoMessage[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

    useEffect(() => () => { timers.current.forEach(clearTimeout); }, []);

    const sendMessage = (text: string) => {
        const content = text.trim();
        if (!content) return;
        setMessages((prev) => [...prev, { id: newId(), role: "user", content, timestamp: new Date().toISOString() }]);
        setIsTyping(true);
        const timer = setTimeout(() => {
            const reply = stubReply(content);
            setMessages((prev) => [...prev, { id: newId(), role: "assistant", ...reply, timestamp: new Date().toISOString() }]);
            setIsTyping(false);
        }, REPLY_DELAY_MS);
        timers.current.push(timer);
    };

    return { messages, isTyping, sendMessage };
}
