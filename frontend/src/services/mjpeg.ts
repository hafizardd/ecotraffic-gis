// Length-delimited JPEG parts; allocate each frame once and decode only complete frames.
export async function readMjpeg(body: ReadableStream<Uint8Array>, onFrame: (jpeg: Uint8Array<ArrayBuffer>, metadata: { id?: string; ageMs: number }) => Promise<void>) {
    const reader = body.getReader();
    let header: number[] = [];
    let frame: Uint8Array<ArrayBuffer> | null = null;
    let offset = 0;
    let metadata: { id?: string; ageMs: number } = { ageMs: 0 };
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) throw new Error('Video stream ended');
            let cursor = 0;
            while (cursor < value.length) {
                if (frame) {
                    const count = Math.min(frame.length - offset, value.length - cursor);
                    frame.set(value.subarray(cursor, cursor + count), offset);
                    offset += count; cursor += count;
                    if (offset === frame.length) { await onFrame(frame, metadata); frame = null; offset = 0; }
                } else {
                    header.push(value[cursor++]);
                    if (header.length > 8192) throw new Error('Invalid MJPEG header');
                    const n = header.length;
                    if (n >= 4 && header[n-4] === 13 && header[n-3] === 10 && header[n-2] === 13 && header[n-1] === 10) {
                        const text = new TextDecoder().decode(new Uint8Array(header));
                        const age = Number(/x-frame-age-ms:\s*(\d+)/i.exec(text)?.[1] ?? 0);
                        metadata = { id: /x-frame-id:[ \t]*([^\r\n]+)/i.exec(text)?.[1], ageMs: Number.isFinite(age) ? age : 0 };
                        const size = Number(/content-length:\s*(\d+)/i.exec(text)?.[1]);
                        if (!Number.isSafeInteger(size) || size < 1 || size > 16 * 1024 * 1024) throw new Error('Invalid MJPEG frame size');
                        frame = new Uint8Array(size); header = [];
                    }
                }
            }
        }
    } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
