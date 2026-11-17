import assert from "node:assert/strict";
import { test } from "node:test";
import { TTS } from "../src/lib/config.ts";
import { buildTtsRequest, requireApiKey, synthesizeWithTimestamps, type TtsRequest } from "../scripts/lib/elevenlabs.ts";

const request: TtsRequest = {
  apiKey: "sk_test_not_a_real_key",
  voiceId: "voice/with space",
  modelId: TTS.modelId,
  text: "น้ำคือชีวิต",
  languageCode: TTS.languageCode,
  voiceSettings: TTS.voiceSettings,
  outputFormat: TTS.outputFormat,
};

test("the request asks for Thai with character timestamps and never sets a speed", () => {
  const { url, init } = buildTtsRequest(request);
  assert.equal(url, "https://api.elevenlabs.io/v1/text-to-speech/voice%2Fwith%20space/with-timestamps?output_format=mp3_44100_128");
  const headers = init.headers as Record<string, string>;
  assert.equal(headers["xi-api-key"], request.apiKey);
  const body = JSON.parse(String(init.body));
  assert.equal(body.model_id, "eleven_v4");
  assert.equal(body.language_code, "th");
  assert.deepEqual(Object.keys(body.voice_settings).sort(), ["similarity_boost", "stability"]);
  assert.ok(!JSON.stringify(body).includes("speed"), "narration speed must never be changed");
});

test("a with-timestamps response gives the audio and its character timing", async () => {
  const fakeFetch = (async () =>
    new Response(
      JSON.stringify({
        audio_base64: Buffer.from("ID3 fake mp3").toString("base64"),
        alignment: { characters: ["น"], character_start_times_seconds: [0], character_end_times_seconds: [0.1] },
      }),
      { status: 200, headers: { "request-id": "req-1", "x-character-count": "11" } },
    )) as typeof fetch;
  const result = await synthesizeWithTimestamps(request, fakeFetch);
  assert.equal(result.audio.toString(), "ID3 fake mp3");
  assert.deepEqual(result.alignment?.characters, ["น"]);
  assert.equal(result.requestId, "req-1");
  assert.equal(result.characterCount, "11");
});

test("API errors explain what to do and never echo the key", async () => {
  const fakeFetch = (async () => new Response('{"detail":"invalid_api_key"}', { status: 401 })) as typeof fetch;
  await assert.rejects(synthesizeWithTimestamps(request, fakeFetch), (error: Error) => {
    assert.match(error.message, /401/);
    assert.match(error.message, /API key was rejected/);
    assert.ok(!error.message.includes(request.apiKey));
    return true;
  });
});

test("a missing key is reported with setup instructions", () => {
  const saved = process.env.ELEVENLABS_API_KEY;
  delete process.env.ELEVENLABS_API_KEY;
  try {
    assert.throws(() => requireApiKey(), /ELEVENLABS_API_KEY is not set[\s\S]*GitHub Actions[\s\S]*pipeline:test/);
  } finally {
    if (saved !== undefined) process.env.ELEVENLABS_API_KEY = saved;
  }
});
