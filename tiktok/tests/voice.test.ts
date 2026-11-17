import assert from "node:assert/strict";
import { test } from "node:test";
import { TTS } from "../src/lib/config.ts";
import { buildTtsRequest } from "../scripts/lib/elevenlabs.ts";
import { describeVoice, resolveVoice } from "../scripts/lib/voice.ts";

test("Madame Scientia is the channel narrator and the default voice", () => {
  assert.deepEqual(TTS.narrator, { name: "Madame Scientia", voiceId: "XAF1635HwW2TJGfbLzfc", language: "th" });
  assert.deepEqual(resolveVoice({}), { voiceId: "XAF1635HwW2TJGfbLzfc", source: "project default", isNarrator: true });
  assert.equal(describeVoice(resolveVoice({})), "Madame Scientia (XAF1635HwW2TJGfbLzfc)");
});

test("an unset GitHub variable (empty string) keeps the narrator", () => {
  assert.equal(resolveVoice({ env: "", episode: "  " }).voiceId, "XAF1635HwW2TJGfbLzfc");
});

test("explicit choices override in order: --voice, ELEVENLABS_VOICE_ID, episode", () => {
  const other = "JBFqnCBsd6RMkjVDRZzb";
  assert.equal(resolveVoice({ option: other, env: "EXAVITQu4vr4xnSDxMaL" }).source, "--voice option");
  assert.equal(resolveVoice({ env: other, episode: "EXAVITQu4vr4xnSDxMaL" }).source, "ELEVENLABS_VOICE_ID");
  const fromEpisode = resolveVoice({ episode: other });
  assert.equal(fromEpisode.source, "episode voice.voiceId");
  assert.equal(fromEpisode.isNarrator, false);
  assert.match(describeVoice(fromEpisode), /not the channel narrator Madame Scientia/);
  assert.equal(resolveVoice({ env: "XAF1635HwW2TJGfbLzfc" }).isNarrator, true);
});

test("a malformed voice id is rejected instead of being sent", () => {
  assert.throws(() => resolveVoice({ env: "Madame Scientia" }), /not a valid ElevenLabs voice id/);
});

test("narration requests go to the narrator's voice in Thai", () => {
  const { url, init } = buildTtsRequest({
    apiKey: "not-a-real-key",
    voiceId: resolveVoice({}).voiceId,
    modelId: TTS.modelId,
    text: "ทดสอบ",
    languageCode: TTS.languageCode,
    voiceSettings: TTS.voiceSettings,
    outputFormat: TTS.outputFormat,
  });
  assert.ok(url.startsWith("https://api.elevenlabs.io/v1/text-to-speech/XAF1635HwW2TJGfbLzfc/with-timestamps"));
  assert.equal(JSON.parse(String(init.body)).language_code, "th");
});
