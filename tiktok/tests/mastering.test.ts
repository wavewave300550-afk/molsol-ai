/**
 * Regression tests for narration mastering with real FFmpeg (Remotion's).
 *
 * The bug: an ElevenLabs MP3 (mp3_44100_128) failed mastering with
 * "Mastering changed the narration length (19.879184 s -> 19.84 s)" although
 * nothing was lost. The MP3's header duration counts whole frames including
 * the encoder delay and padding (761 frames x 1152 = 876,672 samples), while
 * the decoder returns only the narration (874,944 samples = 19.84 s). The
 * fixture here is made the same way (libmp3lame through FFmpeg, so it has the
 * same LAME "Info" header with encoder delay and padding).
 */
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, describe, test } from "node:test";
import { audioDurationSeconds, checkMaster, decodeAudio, ffmpeg, ffprobeJson, masterNarration, renderMaster } from "../scripts/lib/ffmpeg.ts";
import { samplesAtRate } from "../scripts/lib/pcm.ts";
import { planSyntheticNarration, type SyntheticPlan, writeSyntheticWav } from "../scripts/lib/test-audio.ts";

const dir = mkdtempSync(join(tmpdir(), "mastering-test-"));
const wav = join(dir, "source.wav");
const mp3 = join(dir, "take.mp3");
const master = join(dir, "narration.wav");
let plan: SyntheticPlan;
let sourceSamples: number;

/** The gapless fields of an MP3's LAME/Xing header: frames, encoder delay and padding. */
function mp3GaplessInfo(file: string) {
  const data = readFileSync(file);
  let pos = 0;
  if (data.toString("latin1", 0, 3) === "ID3") pos = 10 + ((data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]);
  const mono = ((data.readUInt32BE(pos) >> 6) & 3) === 3;
  const tag = pos + 4 + (mono ? 17 : 32);
  assert.match(data.toString("latin1", tag, tag + 4), /Info|Xing/, "the MP3 has a LAME/Xing header");
  const flags = data.readUInt32BE(tag + 4);
  let p = tag + 8;
  const frames = flags & 1 ? data.readUInt32BE(p) : 0;
  p += (flags & 1 ? 4 : 0) + (flags & 2 ? 4 : 0) + (flags & 4 ? 100 : 0) + (flags & 8 ? 4 : 0);
  const delayPadding = data.readUIntBE(p + 21, 3);
  return { frames, delay: delayPadding >> 12, padding: delayPadding & 0xfff };
}

before(async () => {
  plan = planSyntheticNarration("น้ำหนึ่งโมเลกุล ประกอบด้วยไฮโดรเจนสองอะตอม และออกซิเจนหนึ่งอะตอม", []);
  writeSyntheticWav(wav, plan, 44100);
  sourceSamples = Math.ceil(plan.durationSeconds * 44100);
  const encoded = await ffmpeg(["-y", "-i", wav, "-c:a", "libmp3lame", "-b:a", "128k", mp3]);
  assert.equal(encoded.code, 0, encoded.stderr);
});

after(() => rmSync(dir, { recursive: true, force: true }));

// Independent tests (each writes its own files) run side by side: FFmpeg start-up dominates.
describe("mastering with FFmpeg", { concurrency: true }, () => {
  test("an MP3's header duration counts encoder delay and padding; decoding returns exactly the narration", async () => {
    const info = mp3GaplessInfo(mp3);
    assert.ok(info.delay > 0 && info.padding > 0, JSON.stringify(info));
    const header = Number((await ffprobeJson(mp3)).streams[0].duration);
    assert.ok(Math.abs(header - (info.frames * 1152) / 44100) < 1e-5, "ffprobe reports whole frames");

    const decoded = await decodeAudio(mp3);
    assert.equal(decoded.sampleRate, 44100);
    assert.equal(decoded.samples, sourceSamples, "decoding gives back every encoded sample, no more");
    assert.equal(decoded.samples, info.frames * 1152 - info.delay - info.padding);
    // The old check compared these two numbers with a 10 ms tolerance and failed.
    assert.ok(header - decoded.seconds > 0.01, `header ${header} s vs decoded ${decoded.seconds} s`);
    assert.equal(await audioDurationSeconds(mp3), decoded.seconds, "audioDurationSeconds counts decoded samples");
  });

  test("mastering an ElevenLabs-style MP3 keeps every sample (regression for 19.879184 s -> 19.84 s)", async () => {
    const result = await masterNarration(mp3, master);
    const expected = samplesAtRate(sourceSamples, 44100, 48000);
    assert.deepEqual(result.check.problems, []);
    assert.equal(result.check.sourceSamples, sourceSamples);
    assert.equal(result.check.masterRate, 48000);
    assert.equal(result.check.expectedSamples, expected);
    assert.equal(result.check.masterSamples, expected, "exactly the source's length at 48 kHz");
    assert.equal(result.inputSeconds, sourceSamples / 44100, "the input length is the decoded one, not the header's");
    assert.ok(result.outputSeconds >= result.inputSeconds);
    assert.ok(result.check.comparison.worstDifferenceDb < -40, `speech differs by ${result.check.comparison.worstDifferenceDb} dB`);

    const probe = await ffprobeJson(master);
    assert.equal(probe.streams[0].channels, 2, "stereo playback copy");
    assert.equal(probe.streams[0].sample_rate, "48000");
    assert.equal(await audioDurationSeconds(master), expected / 48000);
  });

  test("when the resampler comes up short, silence is added at the end and the copy passes", async () => {
    const expected = samplesAtRate(sourceSamples, 44100, 48000);
    const padded = join(dir, "padded.wav");
    // Ask for 100 more samples than the resampler gives: apad must fill them with silence.
    await renderMaster(mp3, padded, { gainDb: -3, lengthSamples: expected + 100 });
    const check = await checkMaster(mp3, padded);
    assert.equal(check.masterSamples, expected + 100);
    assert.equal(check.paddedSamples, 100);
    assert.deepEqual(check.problems, []);
  });

  test("the safety check still rejects a copy that lost one sample or was altered", async () => {
    const expected = samplesAtRate(sourceSamples, 44100, 48000);
    const good = join(dir, "good.wav");
    await renderMaster(mp3, good, { gainDb: 2, lengthSamples: expected });
    assert.deepEqual((await checkMaster(mp3, good)).problems, []);
    const short = join(dir, "short.wav");
    const trimmed = await ffmpeg(["-y", "-i", good, "-af", `atrim=end_sample=${expected - 1}`, "-c:a", "pcm_s16le", short]);
    assert.equal(trimmed.code, 0, trimmed.stderr);
    assert.deepEqual((await checkMaster(mp3, short)).problems, ["is 1 sample (0.0 ms) shorter than the source"]);

    const word = plan.words[2];
    const altered = join(dir, "altered.wav");
    const quieter = `volume=0.5:enable='between(t,${word.start.toFixed(3)},${(word.start + 0.1).toFixed(3)})'`;
    const processed = await ffmpeg(["-y", "-i", good, "-af", quieter, "-c:a", "pcm_s16le", altered]);
    assert.equal(processed.code, 0, processed.stderr);
    const check = await checkMaster(mp3, altered);
    assert.equal(check.masterSamples, expected, "same length");
    assert.match(check.problems.join(), /differs from the source at/);
  });

  test("a silent file is refused before any playback copy is written", async () => {
    const silent = join(dir, "silent.wav");
    writeSyntheticWav(silent, { durationSeconds: 1, words: [], alignment: { characters: [], character_start_times_seconds: [], character_end_times_seconds: [] } });
    const out = join(dir, "silent-master.wav");
    writeFileSync(out, "earlier copy");
    await assert.rejects(masterNarration(silent, out), /is silent/);
    assert.equal(readFileSync(out, "utf8"), "earlier copy");
    assert.ok(existsSync(out));
  });
});
