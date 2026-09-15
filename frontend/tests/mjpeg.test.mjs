import test from 'node:test';
import assert from 'node:assert/strict';
import { readMjpeg } from '../src/services/mjpeg.ts';

const encoder = new TextEncoder();
const part = bytes => Buffer.concat([Buffer.from(`--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ${bytes.length}\r\n\r\n`), Buffer.from(bytes), Buffer.from('\r\n')]);

test('fragmented headers and binary frames are decoded exactly once in order', async () => {
    const expected = [[255, 216, 13, 10, 13, 10, 0, 255, 217], [1, 2, 3]];
    const bytes = Buffer.concat(expected.map(part));
    for (const size of [1, 7, bytes.length]) {
        const frames = [];
        const stream = new ReadableStream({ start(controller) {
            for (let i = 0; i < bytes.length; i += size) controller.enqueue(bytes.subarray(i, i + size));
            controller.close();
        } });
        await assert.rejects(readMjpeg(stream, async frame => { frames.push([...frame]); }), /ended/);
        assert.deepEqual(frames, expected);
        assert.equal(stream.locked, false);
    }
});

test('truncated frame is never displayed', async () => {
    let rendered = false;
    const bytes = part([1, 2, 3]);
    const stream = new ReadableStream({ start(c) { c.enqueue(bytes.subarray(0, bytes.length - 3)); c.close(); } });
    await assert.rejects(readMjpeg(stream, async () => { rendered = true; }), /ended/);
    assert.equal(rendered, false);
});

test('invalid size cancels the stream without allocating an unbounded frame', async () => {
    let cancelled = false;
    const stream = new ReadableStream({ start(c) { c.enqueue(encoder.encode('--frame\r\nContent-Length: 9999999999\r\n\r\n')); }, cancel() { cancelled = true; } });
    await assert.rejects(readMjpeg(stream, async () => {}), /Invalid/);
    assert.equal(cancelled, true);
});

test('decoder failure cancels the connection', async () => {
    let cancelled = false;
    const stream = new ReadableStream({ start(c) { c.enqueue(part([1])); }, cancel() { cancelled = true; } });
    await assert.rejects(readMjpeg(stream, async () => { throw new Error('decode'); }), /decode/);
    assert.equal(cancelled, true);
});

 test('frame identity and server age survive fragmented multipart headers', async () => {
    const bytes = encoder.encode('--frame\r\nContent-Length: 1\r\nX-Frame-Id: 123.45\r\nX-Frame-Age-Ms: 42000\r\n\r\nx');
    const stream = new ReadableStream({start(c) { for (const b of bytes) c.enqueue(new Uint8Array([b])); c.close(); }});
    let metadata;
    await assert.rejects(readMjpeg(stream, async (_, value) => { metadata = value; }), /ended/);
    assert.deepEqual(metadata, {id: '123.45', ageMs: 42000});
});
