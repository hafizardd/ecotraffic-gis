import test from "node:test";
import assert from "node:assert/strict";
import { suggestedQuestions } from "../src/utils/bangjoSuggestedQuestions.ts";

test("always includes one meta question first", () => {
    const questions = suggestedQuestions({ target: null, timeMode: "replay" });
    assert.equal(questions.length, 3);
    assert.match(questions[0], /ecotraffic/i);
});

test("mode question follows the live/replay lens", () => {
    const live = suggestedQuestions({ target: null, timeMode: "live" });
    const replay = suggestedQuestions({ target: null, timeMode: "replay" });
    assert.match(live[1], /ramai sekarang/i);
    assert.match(replay[1], /jam segini/i);
});

test("third question follows the selected object", () => {
    assert.match(suggestedQuestions({ target: "segment", timeMode: "replay" })[2], /koridor ini/i);
    assert.match(suggestedQuestions({ target: "hex", timeMode: "replay" })[2], /sel ini/i);
    assert.match(suggestedQuestions({ target: "stop", timeMode: "live" })[2], /halte ini/i);
});

test("falls back to a generic data question without a selection", () => {
    const questions = suggestedQuestions({ target: null, timeMode: "replay" });
    assert.match(questions[2], /emisinya paling tinggi/i);
});
