import assert from "node:assert/strict";
import { test } from "node:test";
import { assessMaster, channelSamples, compareWaveforms, MASTER_LIMITS, parseWav, samplesAtRate, speechSpan } from "../scripts/lib/pcm.ts";

/** Speech-like test signal: syllables of voiced tones with silent gaps. */
function speechLike(seconds: number, rate = 48000): Float32Array {
  const out = new Float32Array(Math.round(seconds * rate));
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    const syllable = Math.max(0, Math.sin(Math.PI * 4 * t)) ** 2;
    out[i] = 0.4 * syllable * (Math.sin(2 * Math.PI * 180 * t) + 0.5 * Math.sin(2 * Math.PI * 720 * t + 1) + 0.25 * Math.sin(2 * Math.PI * 2300 * t + 2));
  }
  return out;
}

const scaled = (pcm: Float32Array, gain: number) => pcm.map((v) => v * gain);
const withLength = (pcm: Float32Array, length: number) => {
  const out = new Float32Array(length);
  out.set(pcm.subarray(0, Math.min(length, pcm.length)));
  return out;
};
const assess = (reference: Float32Array, master: Float32Array, sourceSamples = reference.length, sourceRate = 48000) =>
  assessMaster({ sourceSamples, sourceRate, reference, master, masterRate: 48000 });

test("reads WAV streamed by FFmpeg: unknown sizes, extensible 24-bit format, extra chunks", () => {
  const fmt = Buffer.alloc(8 + 40);
  fmt.write("fmt ", 0, "latin1");
  fmt.writeUInt32LE(40, 4);
  fmt.writeUInt16LE(0xfffe, 8); // WAVE_FORMAT_EXTENSIBLE
  fmt.writeUInt16LE(1, 10); // mono
  fmt.writeUInt32LE(44100, 12);
  fmt.writeUInt32LE(44100 * 3, 16);
  fmt.writeUInt16LE(3, 20); // block align
  fmt.writeUInt16LE(24, 22);
  const list = Buffer.from("LIST\x04\x00\x00\x00INFO", "latin1");
  const data = Buffer.alloc(8 + 9);
  data.write("data", 0, "latin1");
  data.writeUInt32LE(0xffffffff, 4); // a pipe cannot be rewound to fill this in
  data.writeIntLE(4194304, 8, 3); // 0.5
  data.writeIntLE(-8388608, 11, 3); // -1
  data.writeIntLE(0, 14, 3);
  const head = Buffer.from("RIFF\xff\xff\xff\xffWAVE", "latin1");
  const wav = parseWav(Buffer.concat([head, fmt, list, data]));
  assert.equal(wav.sampleRate, 44100);
  assert.equal(wav.frames, 3);
  assert.deepEqual(Array.from(channelSamples(wav)), [0.5, -1, 0]);
});

test("reads 16-bit stereo WAV and stops at a data chunk cut short", () => {
  const header = Buffer.alloc(44);
  header.write("RIFF", 0, "latin1");
  header.writeUInt32LE(36 + 400, 4);
  header.write("WAVEfmt ", 8, "latin1");
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(2, 22);
  header.writeUInt32LE(48000, 24);
  header.writeUInt32LE(48000 * 4, 28);
  header.writeUInt16LE(4, 32);
  header.writeUInt16LE(16, 34);
  header.write("data", 36, "latin1");
  header.writeUInt32LE(400, 40); // says 100 frames
  const samples = Buffer.alloc(4 * 3 + 2); // but only 3 whole frames arrived
  samples.writeInt16LE(16384, 0);
  samples.writeInt16LE(-16384, 2);
  const wav = parseWav(Buffer.concat([header, samples]));
  assert.equal(wav.channels, 2);
  assert.equal(wav.frames, 3);
  assert.equal(channelSamples(wav, 0)[0], 0.5);
  assert.equal(channelSamples(wav, 1)[0], -0.5);
  assert.throws(() => parseWav(Buffer.from("not a wav file at all")), /Not a WAV/);
});

test("lengths convert between sample rates exactly and never get shorter", () => {
  // The failed ElevenLabs take: 874,944 decoded samples at 44.1 kHz = 19.84 s.
  assert.equal(samplesAtRate(874944, 44100, 48000), 952320);
  assert.equal(samplesAtRate(44101, 44100, 48000), 48002);
  assert.equal(samplesAtRate(1, 44100, 48000), 2);
  for (const rate of [8000, 16000, 22050, 24000, 32000, 44100, 96000]) {
    for (const n of [1, 999, 44101, 874944, 2_646_001]) {
      const out = samplesAtRate(n, rate, 48000);
      assert.ok(out / 48000 >= n / rate, `${n} at ${rate} Hz must not get shorter`);
      assert.ok((out - 1) / 48000 < n / rate, `${n} at ${rate} Hz rounds up by less than one sample`);
    }
  }
});

test("an exact copy at a constant gain passes, with nothing added", () => {
  const source = speechLike(1.5);
  const result = assess(source, scaled(source, 0.7));
  assert.deepEqual(result.problems, []);
  assert.equal(result.masterSamples, result.expectedSamples);
  assert.equal(result.paddedSamples, 0);
  assert.ok(result.comparison.speechWindows > 30);
  assert.ok(result.comparison.worstDifferenceDb < -100);
  assert.ok(Math.abs(result.comparison.gainDb - 20 * Math.log10(0.7)) < 0.01);
});

test("one missing sample fails: the check is sample-accurate", () => {
  const source = speechLike(1);
  const result = assess(source, withLength(source, source.length - 1));
  assert.deepEqual(result.problems, ["is 1 sample (0.0 ms) shorter than the source"]);
});

test("silence added at the end to reach the full length passes; anything else does not", () => {
  const source = speechLike(1);
  // A resampler that came up 7 samples short of the source's length, padded with silence.
  const reference = source.subarray(0, source.length - 7);
  const padded = assess(reference, withLength(reference, source.length), source.length);
  assert.deepEqual(padded.problems, []);
  assert.equal(padded.paddedSamples, 7);

  const unpadded = assess(reference, reference, source.length);
  assert.deepEqual(unpadded.problems, ["is 7 samples (0.1 ms) shorter than the source"]);

  const noisy = withLength(reference, source.length);
  noisy[source.length - 1] = 0.01;
  assert.match(assess(reference, noisy, source.length).problems.join(), /has sound after the narration ends/);

  const extra = Math.round(MASTER_LIMITS.maxExtraSeconds * 48000) + 1;
  assert.match(assess(source, withLength(source, source.length + extra)).problems.join(), /longer than the source/);
});

test("a cut, a shift, a dropout, a speed change or level processing is caught even at full length", () => {
  const source = speechLike(2);
  const differs = (master: Float32Array) => assess(source, master).problems.some((p) => p.startsWith("differs from the source"));

  // Shifted by one sample (same length).
  const shifted = new Float32Array(source.length);
  shifted.set(source.subarray(0, source.length - 1), 1);
  assert.ok(differs(shifted));

  // 20 ms of speech dropped and the rest moved up, padded back to length.
  const cut = new Float32Array(source.length);
  const at = Math.round(0.6 * 48000);
  cut.set(source.subarray(0, at));
  cut.set(source.subarray(at + 960), at);
  assert.ok(differs(cut));

  // 30 ms of speech silenced in place.
  const dropout = source.slice();
  dropout.fill(0, Math.round(1.1 * 48000), Math.round(1.13 * 48000));
  assert.ok(differs(dropout));

  // 0.1% slower: only 2 ms longer (within the length limit), but every word drifts.
  const slower = new Float32Array(Math.round(source.length * 1.001));
  for (let i = 0; i < slower.length; i++) {
    const x = i / 1.001;
    const j = Math.floor(x);
    slower[i] = j + 1 < source.length ? source[j] + (source[j + 1] - source[j]) * (x - j) : 0;
  }
  assert.ok(differs(slower));

  // Half a second turned down by 6 dB (what a compressor or limiter does).
  const compressed = source.map((v, i) => (i > 48000 && i < 72000 ? v * 0.5 : v));
  assert.ok(differs(compressed));
});

test("comparison ignores silence between words and needs speech to compare", () => {
  const source = speechLike(1);
  const quietNoise = source.map((v, i) => (Math.abs(v) < 1e-6 ? ((i % 7) - 3) * 1e-7 : v));
  assert.deepEqual(assess(source, quietNoise).problems, []);
  assert.deepEqual(assess(new Float32Array(4800), new Float32Array(4800)).problems, ["cannot be compared: the source holds no speech"]);
  assert.equal(compareWaveforms(source, new Float32Array(source.length), 48000).worstDifferenceDb, Number.POSITIVE_INFINITY);
});

test("speech start and end do not depend on how long the silence after the last word is", () => {
  const rate = 48000;
  // Like the ElevenLabs take: speech, then only 145 ms of silence. In the video the
  // 0.8 s tail lengthens that silence; both must report the same end of speech.
  const narration = new Float32Array(Math.round(1.145 * rate));
  for (let i = Math.round(0.1 * rate); i < rate; i++) narration[i] = 0.5 * Math.sin((2 * Math.PI * 220 * i) / rate);
  const video = new Float32Array(narration.length + Math.round(0.8 * rate)).map((_, i) => (i < narration.length ? narration[i] : 1e-5 * ((i % 5) - 2)));
  assert.deepEqual(speechSpan(narration, rate), { start: 0.1, end: 1 });
  assert.deepEqual(speechSpan(video, rate), { start: 0.1, end: 1 });
  assert.equal(speechSpan(new Float32Array(rate), rate), null);
});
