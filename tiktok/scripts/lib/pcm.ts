/**
 * Sample-level audio checks, with no FFmpeg and no files: reading PCM WAV
 * data, exact lengths across sample rates, and proving that a mastered copy
 * still holds every sample of the narration it was made from.
 *
 * Why samples and not the "duration" a file reports: an MP3's duration counts
 * whole MP3 frames (1152 samples each), including the encoder delay at the
 * start and the padding at the end. Decoders remove both (gapless playback,
 * from the LAME/Xing "Info" header), so the audio is shorter than the
 * header says: an ElevenLabs mp3_44100_128 take reports 576 + 1152 samples
 * (39 ms) more than it holds. Only decoded samples tell the real length.
 */

export type Wav = {
  sampleRate: number;
  channels: number;
  bitsPerSample: number;
  /** Sample frames: one sample per channel. */
  frames: number;
  /** The interleaved little-endian PCM bytes. */
  data: Buffer;
};

const WAVE_FORMAT_PCM = 1;
const WAVE_FORMAT_EXTENSIBLE = 0xfffe;
const SIZE_UNKNOWN = 0xffffffff;

/**
 * Reads a 16- or 24-bit PCM WAV. FFmpeg writing to a pipe cannot go back and
 * fill in the sizes, so a data size of 0xFFFFFFFF (or past the end) means
 * "everything up to the end of the file".
 */
export function parseWav(buffer: Buffer): Wav {
  if (buffer.length < 12 || buffer.toString("latin1", 0, 4) !== "RIFF" || buffer.toString("latin1", 8, 12) !== "WAVE") {
    throw new Error("Not a WAV file.");
  }
  let format: { tag: number; channels: number; sampleRate: number; blockAlign: number; bitsPerSample: number } | null = null;
  let offset = 12;
  while (offset + 8 <= buffer.length) {
    const id = buffer.toString("latin1", offset, offset + 4);
    const size = buffer.readUInt32LE(offset + 4);
    const body = offset + 8;
    if (id === "fmt ") {
      format = {
        tag: buffer.readUInt16LE(body),
        channels: buffer.readUInt16LE(body + 2),
        sampleRate: buffer.readUInt32LE(body + 4),
        blockAlign: buffer.readUInt16LE(body + 12),
        bitsPerSample: buffer.readUInt16LE(body + 14),
      };
    } else if (id === "data") {
      if (!format) throw new Error("The WAV data comes before its format.");
      if (format.tag !== WAVE_FORMAT_PCM && format.tag !== WAVE_FORMAT_EXTENSIBLE) throw new Error(`The WAV is not PCM (format ${format.tag}).`);
      if (format.bitsPerSample !== 16 && format.bitsPerSample !== 24) throw new Error(`Only 16- and 24-bit WAV is read (got ${format.bitsPerSample}-bit).`);
      if (format.blockAlign !== (format.channels * format.bitsPerSample) / 8) throw new Error("The WAV format block is inconsistent.");
      const available = buffer.length - body;
      const bytes = size === SIZE_UNKNOWN || size > available ? available : size;
      const frames = Math.floor(bytes / format.blockAlign);
      return {
        sampleRate: format.sampleRate,
        channels: format.channels,
        bitsPerSample: format.bitsPerSample,
        frames,
        data: buffer.subarray(body, body + frames * format.blockAlign),
      };
    }
    if (size === SIZE_UNKNOWN) break;
    offset = body + size + (size % 2);
  }
  throw new Error("The WAV file has no audio data.");
}

/** One channel of a WAV as floats in [-1, 1). */
export function channelSamples(wav: Wav, channel = 0): Float32Array {
  if (channel >= wav.channels) throw new Error(`The WAV has ${wav.channels} channel(s), not ${channel + 1}.`);
  const bytes = wav.bitsPerSample / 8;
  const stride = wav.channels * bytes;
  const out = new Float32Array(wav.frames);
  let p = channel * bytes;
  if (bytes === 2) {
    for (let i = 0; i < wav.frames; i++, p += stride) out[i] = wav.data.readInt16LE(p) / 32768;
  } else {
    for (let i = 0; i < wav.frames; i++, p += stride) out[i] = wav.data.readIntLE(p, 3) / 8388608;
  }
  return out;
}

/**
 * Samples needed at `toRate` to last at least as long as `samples` at
 * `fromRate`: rounded up, so converting never shortens. Exact for any real
 * narration length (the product stays far below 2^53).
 */
export function samplesAtRate(samples: number, fromRate: number, toRate: number): number {
  return Math.ceil((samples * toRate) / fromRate);
}

export const toDb = (ratio: number): number => (ratio > 0 ? 20 * Math.log10(ratio) : Number.NEGATIVE_INFINITY);

/**
 * Where speech starts and ends, in seconds: the first and last 5 ms window
 * within `rangeDb` of the loudest one. Works on any version of a narration
 * (the WAV, the video's AAC track) without a minimum pause length, so two
 * versions can be compared directly. Null for silence.
 */
export function speechSpan(pcm: Float32Array, sampleRate: number, rangeDb = 40): { start: number; end: number } | null {
  const window = Math.max(1, Math.round(sampleRate * 0.005));
  const count = Math.ceil(pcm.length / window);
  const power = new Float64Array(count);
  for (let i = 0; i < pcm.length; i++) power[Math.floor(i / window)] += pcm[i] * pcm[i];
  let loudest = 0;
  for (let w = 0; w < count; w++) {
    power[w] /= Math.min(window, pcm.length - w * window);
    loudest = Math.max(loudest, power[w]);
  }
  if (loudest === 0) return null;
  const threshold = loudest * 10 ** (-rangeDb / 10);
  let first = -1;
  let last = -1;
  for (let w = 0; w < count; w++) {
    if (power[w] < threshold) continue;
    if (first < 0) first = w;
    last = w;
  }
  return { start: (first * window) / sampleRate, end: Math.min(pcm.length, (last + 1) * window) / sampleRate };
}

export const WAVEFORM_COMPARISON = {
  /** Compared in 20 ms windows. */
  windowSeconds: 0.02,
  /** A window holds speech when it is within this many dB of the loudest window. */
  speechRangeDb: 40,
};

export type WaveformComparison = {
  /** 20 ms windows of the reference that hold speech. */
  speechWindows: number;
  /**
   * The largest difference between the copy and the reference in any speech
   * window, after one constant gain, in dB relative to that window (lower is
   * closer; -Infinity means identical).
   */
  worstDifferenceDb: number;
  worstAtSeconds: number;
  /** The constant gain that maps the reference onto the copy (least squares). */
  gainDb: number;
};

/**
 * Compares a copy with its reference sample by sample, allowing one constant
 * gain: a cut, a dropout, a shift of even one sample, a speed change or any
 * level processing (compression, limiting) shows up as a large difference in
 * some speech window. Both must have the same sample rate; samples the copy
 * lacks count as silence.
 */
export function compareWaveforms(reference: Float32Array, copy: Float32Array, sampleRate: number): WaveformComparison {
  const overlap = Math.min(reference.length, copy.length);
  let cross = 0;
  let power = 0;
  for (let i = 0; i < overlap; i++) {
    cross += reference[i] * copy[i];
    power += reference[i] * reference[i];
  }
  const gain = power > 0 ? cross / power : 0;

  const window = Math.max(1, Math.round(sampleRate * WAVEFORM_COMPARISON.windowSeconds));
  const count = Math.ceil(reference.length / window);
  const level = new Float64Array(count);
  const difference = new Float64Array(count);
  for (let i = 0; i < reference.length; i++) {
    const w = Math.floor(i / window);
    const r = reference[i];
    const d = (i < copy.length ? copy[i] : 0) - gain * r;
    level[w] += r * r;
    difference[w] += d * d;
  }
  let loudest = 0;
  for (const e of level) loudest = Math.max(loudest, e);
  const threshold = loudest * 10 ** (-WAVEFORM_COMPARISON.speechRangeDb / 10);

  let speechWindows = 0;
  let worstDifferenceDb = Number.NEGATIVE_INFINITY;
  let worstAtSeconds = 0;
  for (let w = 0; w < count; w++) {
    if (loudest === 0 || level[w] < threshold) continue;
    speechWindows++;
    const expected = gain * gain * level[w];
    const db = expected > 0 ? 10 * Math.log10(difference[w] / expected) : Number.POSITIVE_INFINITY;
    if (db > worstDifferenceDb) {
      worstDifferenceDb = db;
      worstAtSeconds = (w * window) / sampleRate;
    }
  }
  return { speechWindows, worstDifferenceDb, worstAtSeconds, gainDb: toDb(Math.abs(gain)) };
}

export const MASTER_LIMITS = {
  /** Longest the playback copy may run past the narration (resampler rounding). */
  maxExtraSeconds: 0.01,
  /** Added samples must be silence: at most 2 steps of 16-bit audio (-84 dBFS). */
  silencePeak: 2 / 32768,
  /** Every speech window must match the source this closely (dB, relative). */
  maxDifferenceDb: -30,
};

export type MasterAssessment = {
  sourceRate: number;
  /** Decoded samples of the source: its exact length. */
  sourceSamples: number;
  masterRate: number;
  masterSamples: number;
  /** The source's length at the master's rate, rounded up: the shortest the master may be. */
  expectedSamples: number;
  /** Silence after the resampled narration, added to reach the full length. */
  paddedSamples: number;
  comparison: WaveformComparison;
  /** Each finished clause completes "The playback copy ...". Empty when the master is good. */
  problems: string[];
};

/**
 * Decides whether a mastered copy holds the whole narration. `reference` is
 * the source decoded at the master's rate with the same resampler (and no
 * gain), so the two must match sample for sample at one constant gain.
 */
export function assessMaster(input: {
  sourceSamples: number;
  sourceRate: number;
  reference: Float32Array;
  master: Float32Array;
  masterRate: number;
}): MasterAssessment {
  const { sourceSamples, sourceRate, reference, master, masterRate } = input;
  const expectedSamples = samplesAtRate(sourceSamples, sourceRate, masterRate);
  const ms = (samples: number) => `${((samples / masterRate) * 1000).toFixed(1)} ms`;
  const problems: string[] = [];

  if (master.length < expectedSamples) {
    const missing = expectedSamples - master.length;
    problems.push(`is ${missing} sample${missing === 1 ? "" : "s"} (${ms(missing)}) shorter than the source`);
  }
  const extra = master.length - expectedSamples;
  if (extra > Math.round(MASTER_LIMITS.maxExtraSeconds * masterRate)) {
    problems.push(`is ${extra} samples (${ms(extra)}) longer than the source`);
  }
  let tailPeak = 0;
  for (let i = reference.length; i < master.length; i++) tailPeak = Math.max(tailPeak, Math.abs(master[i]));
  if (tailPeak > MASTER_LIMITS.silencePeak) {
    problems.push(`has sound after the narration ends (peak ${toDb(tailPeak).toFixed(1)} dBFS)`);
  }
  const comparison = compareWaveforms(reference, master, masterRate);
  if (comparison.speechWindows === 0) {
    problems.push("cannot be compared: the source holds no speech");
  } else if (comparison.worstDifferenceDb > MASTER_LIMITS.maxDifferenceDb) {
    problems.push(
      `differs from the source at ${comparison.worstAtSeconds.toFixed(2)} s (${comparison.worstDifferenceDb.toFixed(1)} dB): ` +
        "part of the narration was cut, moved or processed",
    );
  }
  return {
    sourceRate,
    sourceSamples,
    masterRate,
    masterSamples: master.length,
    expectedSamples,
    paddedSamples: Math.max(0, master.length - reference.length),
    comparison,
    problems,
  };
}

const kHz = (rate: number) => `${Number((rate / 1000).toFixed(2))} kHz`;
const count = (n: number) => n.toLocaleString("en-US");

/** One line for logs and reports, e.g. "874,944 samples at 44.1 kHz → 952,320 at 48 kHz, …". */
export function describeMaster(a: MasterAssessment): string {
  const parts = [
    `${count(a.sourceSamples)} samples at ${kHz(a.sourceRate)} → ${count(a.masterSamples)} at ${kHz(a.masterRate)} ` +
      `(${(a.sourceSamples / a.sourceRate).toFixed(3)} s → ${(a.masterSamples / a.masterRate).toFixed(3)} s)`,
  ];
  if (a.paddedSamples > 0) parts.push(`${count(a.paddedSamples)} samples of silence added at the end`);
  const d = a.comparison.worstDifferenceDb;
  if (a.comparison.speechWindows > 0) parts.push(`speech matches the source to ${Number.isFinite(d) ? `${d.toFixed(0)} dB` : "the sample"}`);
  return parts.join(", ");
}
