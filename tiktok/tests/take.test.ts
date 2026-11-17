import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";
import { TTS } from "../src/lib/config.ts";
import { episodePaths } from "../scripts/lib/paths.ts";
import { findReusableTake, readSavedTake, saveTake, sha256, takeProblems } from "../scripts/lib/take.ts";

const dir = mkdtempSync(join(tmpdir(), "take-test-"));
after(() => rmSync(dir, { recursive: true, force: true }));

const paths = { ...episodePaths("voice-test"), mediaDir: dir, narrationSource: join(dir, "narration.source.mp3"), elevenlabsTake: join(dir, "elevenlabs-take.json") };
const audio = Buffer.from("ID3 pretend this is the MP3 ElevenLabs sent");
const alignment = { characters: ["น", "้", "ำ"], character_start_times_seconds: [0, 0.1, 0.1], character_end_times_seconds: [0.1, 0.1, 0.3] };
const want = { narrationHash: "a".repeat(64), voiceId: TTS.narrator.voiceId, modelId: TTS.modelId };

function save() {
  writeFileSync(paths.narrationSource, audio);
  return saveTake(paths, paths.narrationSource, audio, {
    ...want,
    text: "น้ำ",
    languageCode: "th",
    outputFormat: TTS.outputFormat,
    requestId: "req-1",
    characterCount: "3",
    alignment,
    normalizedAlignment: null,
  });
}

test("a take is saved with its timing and the SHA-256 of its MP3", () => {
  const saved = save();
  assert.equal(saved.audioFile, "narration.source.mp3");
  assert.equal(saved.audioSha256, sha256(audio));
  assert.equal(saved.audioBytes, audio.length);
  const read = readSavedTake(paths.elevenlabsTake);
  assert.deepEqual(read.alignment, alignment);
  assert.equal(read.requestId, "req-1");
  assert.equal(read.episodeId, "voice-test");
});

test("narrate reuses a saved take only for the same script, voice, model and MP3", () => {
  save();
  assert.equal(findReusableTake(paths, want)?.requestId, "req-1");
  assert.equal(findReusableTake(paths, { ...want, narrationHash: "b".repeat(64) }), null, "script changed");
  assert.equal(findReusableTake(paths, { ...want, voiceId: "JBFqnCBsd6RMkjVDRZzb" }), null, "other voice");
  assert.equal(findReusableTake(paths, { ...want, modelId: "eleven_multilingual_v2" }), null, "other model");
  writeFileSync(paths.narrationSource, Buffer.from("a different MP3"));
  assert.equal(findReusableTake(paths, want), null, "the MP3 was replaced");
});

test("a recovered take must match the script and the exact MP3", () => {
  const take = save();
  assert.deepEqual(takeProblems(take, { narrationHash: want.narrationHash, audioSha256: sha256(audio) }), []);
  assert.deepEqual(takeProblems(take, { narrationHash: "c".repeat(64), audioSha256: sha256(Buffer.from("other")) }), [
    "it was made for another version of the script",
    "the audio file is not the one this take was saved with",
  ]);
  const notATake = join(dir, "narration.json");
  writeFileSync(notATake, JSON.stringify({ version: 1, source: "elevenlabs" }));
  assert.throws(() => readSavedTake(notATake), /not a saved ElevenLabs take/);
});
