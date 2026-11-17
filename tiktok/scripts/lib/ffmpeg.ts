/**
 * FFmpeg and FFprobe helpers. They use the binaries that ship with Remotion
 * (`remotion ffmpeg` / `remotion ffprobe`), so nothing extra is installed
 * locally or in CI. Set FFMPEG_BIN / FFPROBE_BIN to use other binaries.
 */
import { spawn } from "node:child_process";
import { closeSync, openSync, readSync, rmSync, statSync } from "node:fs";
import { join } from "node:path";
import type { Interval } from "../../src/lib/alignment.ts";
import { AUDIO_MASTER } from "../../src/lib/config.ts";
import { projectRoot } from "./paths.ts";
import { assessMaster, channelSamples, type MasterAssessment, parseWav, samplesAtRate } from "./pcm.ts";

const remotionBin = join(projectRoot, "node_modules", ".bin", "remotion");

function tool(name: "ffmpeg" | "ffprobe"): { cmd: string; pre: string[] } {
  const override = process.env[name === "ffmpeg" ? "FFMPEG_BIN" : "FFPROBE_BIN"];
  return override ? { cmd: override, pre: [] } : { cmd: remotionBin, pre: [name] };
}

export type RunResult = { code: number; stdout: string; stderr: string };

export function run(
  cmd: string,
  args: string[],
  options: { cwd?: string; inherit?: boolean; env?: NodeJS.ProcessEnv } = {},
): Promise<RunResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: options.cwd ?? projectRoot,
      env: options.env ?? process.env,
      stdio: options.inherit ? "inherit" : ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (d) => (stdout += d));
    child.stderr?.on("data", (d) => (stderr += d));
    child.on("error", reject);
    child.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
  });
}

/** Like run(), but keeps stdout as bytes (decoded audio). */
function runForBytes(cmd: string, args: string[]): Promise<{ code: number; stdout: Buffer; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { cwd: projectRoot, stdio: ["ignore", "pipe", "pipe"] });
    const chunks: Buffer[] = [];
    let stderr = "";
    child.stdout.on("data", (d: Buffer) => chunks.push(d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("error", reject);
    child.on("close", (code) => resolve({ code: code ?? 1, stdout: Buffer.concat(chunks), stderr }));
  });
}

export async function ffmpeg(args: string[]): Promise<RunResult> {
  const { cmd, pre } = tool("ffmpeg");
  return run(cmd, [...pre, "-hide_banner", "-nostats", ...args]);
}

export async function ffprobeJson(file: string): Promise<FfprobeResult> {
  const { cmd, pre } = tool("ffprobe");
  const result = await run(cmd, [...pre, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", file]);
  if (result.code !== 0) throw new Error(`ffprobe could not read ${file}: ${result.stderr.trim()}`);
  return JSON.parse(result.stdout) as FfprobeResult;
}

export type FfprobeStream = {
  codec_type: "video" | "audio" | string;
  codec_name: string;
  codec_tag_string?: string;
  profile?: string;
  level?: number;
  width?: number;
  height?: number;
  pix_fmt?: string;
  r_frame_rate?: string;
  avg_frame_rate?: string;
  nb_frames?: string;
  duration?: string;
  /** Length in time_base units: for PCM audio (time base 1/rate), the sample count. */
  duration_ts?: number;
  time_base?: string;
  sample_rate?: string;
  channels?: number;
};
export type FfprobeResult = { streams: FfprobeStream[]; format: { format_name: string; duration: string; size: string; bit_rate?: string } };

/**
 * Exact length of the first audio stream. A PCM file (WAV) states it exactly;
 * for compressed audio the duration in the header is only an estimate (an
 * MP3's includes the encoder delay and padding that decoding removes), so the
 * audio is decoded and its samples counted.
 */
export async function audioDurationSeconds(file: string): Promise<number> {
  const probe = await ffprobeJson(file);
  const audio = probe.streams.find((s) => s.codec_type === "audio");
  if (!audio) throw new Error(`${file} has no audio stream.`);
  const [num, den] = (audio.time_base ?? "").split("/").map(Number);
  if (audio.codec_name.startsWith("pcm_") && Number.isInteger(audio.duration_ts) && num > 0 && den > 0) {
    return ((audio.duration_ts as number) * num) / den; // samples / rate, not the rounded "duration"
  }
  return (await decodeAudio(file)).seconds;
}

export type DecodedAudio = {
  sampleRate: number;
  /** Every decoded sample (per channel): the exact length. */
  samples: number;
  seconds: number;
  /** The decoded audio, mixed to mono. */
  pcm: Float32Array;
};

/**
 * Decodes the first audio stream completely and counts its samples. The
 * decoder drops an MP3's encoder delay and padding, so this is the real
 * length, unlike the duration in the header. Mono, 24-bit; at `sampleRate`
 * if given, through FFmpeg's default resampler (the one masterNarration uses).
 */
export async function decodeAudio(file: string, options: { sampleRate?: number } = {}): Promise<DecodedAudio> {
  const { cmd, pre } = tool("ffmpeg");
  const rate = options.sampleRate ? ["-ar", String(options.sampleRate)] : [];
  const result = await runForBytes(cmd, [
    ...pre,
    "-hide_banner",
    "-nostats",
    "-v",
    "error",
    "-i",
    file,
    "-map",
    "0:a:0",
    "-ac",
    "1",
    ...rate,
    "-c:a",
    "pcm_s24le",
    "-f",
    "wav",
    "-",
  ]);
  if (result.code !== 0) throw new Error(`Could not decode ${file}: ${result.stderr.slice(-400)}`);
  const wav = parseWav(result.stdout);
  return { sampleRate: wav.sampleRate, samples: wav.frames, seconds: wav.frames / wav.sampleRate, pcm: channelSamples(wav) };
}

export type Loudness = { inputI: number; inputTp: number; inputLra: number; inputThresh: number };

/**
 * EBU R128 loudness of the first audio stream (FFmpeg loudnorm analysis).
 * `stereo` measures after FFmpeg's stereo upmix, i.e. what masterNarration
 * writes: the upmix keeps loudness and lowers each channel's true peak.
 */
export async function measureLoudness(file: string, options: { stereo?: boolean } = {}): Promise<Loudness> {
  const { integratedLufs: I, truePeakDb: TP, loudnessRange: LRA } = AUDIO_MASTER;
  const analysis = `loudnorm=I=${I}:TP=${TP}:LRA=${LRA}:print_format=json`;
  const filter = options.stereo ? `aformat=channel_layouts=stereo,${analysis}` : analysis;
  const result = await ffmpeg(["-i", file, "-map", "0:a:0", "-af", filter, "-f", "null", "-"]);
  const json = result.stderr.slice(result.stderr.lastIndexOf("{"), result.stderr.lastIndexOf("}") + 1);
  if (result.code !== 0 || !json) throw new Error(`Loudness analysis failed for ${file}: ${result.stderr.slice(-400)}`);
  const m = JSON.parse(json) as Record<string, string>;
  return { inputI: Number(m.input_i), inputTp: Number(m.input_tp), inputLra: Number(m.input_lra), inputThresh: Number(m.input_thresh) };
}

export type MasterCheck = MasterAssessment & { sourceSeconds: number; masterSeconds: number };

/**
 * Proves a playback copy holds the whole narration, sample for sample: both
 * files are decoded and their samples counted (never the duration in a file
 * header), the copy must be at least as long as the source, anything extra
 * must be trailing silence, and in every 20 ms of speech the copy must equal
 * the source at one constant gain. See assessMaster in pcm.ts.
 */
export async function checkMaster(source: string, master: string, decodedSource?: DecodedAudio): Promise<MasterCheck> {
  const [original, copy] = await Promise.all([decodedSource ?? decodeAudio(source), decodeAudio(master)]);
  const reference = await decodeAudio(source, { sampleRate: copy.sampleRate });
  const assessment = assessMaster({
    sourceSamples: original.samples,
    sourceRate: original.sampleRate,
    reference: reference.pcm,
    master: copy.pcm,
    masterRate: copy.sampleRate,
  });
  return { ...assessment, sourceSeconds: original.seconds, masterSeconds: copy.seconds };
}

/**
 * Writes the playback copy: one constant gain, FFmpeg's default resampler to
 * 48 kHz, stereo, 16-bit. `lengthSamples` is the least it may hold: if the
 * resampler ever came up short, silence is added at the end (apad), so the
 * narration is never shortened.
 */
export async function renderMaster(input: string, output: string, options: { gainDb: number; lengthSamples: number }): Promise<void> {
  const filter = `volume=${options.gainDb.toFixed(2)}dB,aresample=${AUDIO_MASTER.sampleRate},apad=whole_len=${options.lengthSamples}`;
  const result = await ffmpeg(["-y", "-i", input, "-map", "0:a:0", "-af", filter, "-ac", "2", "-c:a", "pcm_s16le", output]);
  if (result.code !== 0) throw new Error(`Could not master ${input}: ${result.stderr.slice(-400)}`);
}

export type MasterResult = {
  gainDb: number;
  /** Exact lengths from decoded samples. */
  inputSeconds: number;
  outputSeconds: number;
  loudness: Loudness;
  check: MasterCheck;
};

/**
 * Makes the playback copy of the narration: one constant gain toward
 * -14 LUFS (capped so it never clips), 48 kHz. It is written as stereo on
 * purpose: given a mono file, Remotion copies it into both channels at full
 * level and the video comes out about 3 LU louder than intended.
 * A constant gain and resampling leave timing and dynamics untouched. The
 * copy is then checked sample for sample against the source (checkMaster);
 * if it is shorter or differs in any way, it is deleted and the step fails.
 */
export async function masterNarration(input: string, output: string): Promise<MasterResult> {
  const [loudness, source] = await Promise.all([measureLoudness(input, { stereo: true }), decodeAudio(input)]);
  if (!Number.isFinite(loudness.inputI) || loudness.inputI < -70) throw new Error(`${input} is silent; there is no narration to use.`);
  const gainDb = Number(Math.min(AUDIO_MASTER.integratedLufs - loudness.inputI, AUDIO_MASTER.truePeakDb - loudness.inputTp).toFixed(2));
  await renderMaster(input, output, { gainDb, lengthSamples: samplesAtRate(source.samples, source.sampleRate, AUDIO_MASTER.sampleRate) });
  const check = await checkMaster(input, output, source);
  if (check.problems.length > 0) {
    rmSync(output, { force: true });
    throw new Error(
      `Mastering changed the narration, so the result was not kept: the playback copy ${check.problems.join("; ")}. ` +
        "Nothing may shorten, speed up or alter narration.",
    );
  }
  return { gainDb, inputSeconds: check.sourceSeconds, outputSeconds: check.masterSeconds, loudness, check };
}

/** Silent stretches (FFmpeg silencedetect) of the first audio stream. */
export async function detectSilences(file: string, noiseDb: number, minSeconds: number): Promise<Interval[]> {
  const result = await ffmpeg(["-i", file, "-map", "0:a:0", "-af", `silencedetect=noise=${noiseDb.toFixed(1)}dB:d=${minSeconds}`, "-f", "null", "-"]);
  if (result.code !== 0) throw new Error(`Silence detection failed for ${file}: ${result.stderr.slice(-400)}`);
  const silences: Interval[] = [];
  let open: number | null = null;
  for (const line of result.stderr.split("\n")) {
    const start = line.match(/silence_start: (-?[\d.]+)/);
    const end = line.match(/silence_end: (-?[\d.]+)/);
    if (start) open = Math.max(0, Number(start[1]));
    if (end && open !== null) {
      silences.push({ start: open, end: Number(end[1]) });
      open = null;
    }
  }
  if (open !== null) silences.push({ start: open, end: await audioDurationSeconds(file) });
  return silences;
}

/**
 * Silences with a threshold adapted to the recording, as the Remotion
 * silence-detection guide recommends: the loudnorm gating threshold.
 */
export async function detectPauses(file: string, minSeconds = 0.18): Promise<{ silences: Interval[]; thresholdDb: number }> {
  const { inputThresh } = await measureLoudness(file);
  const thresholdDb = Number.isFinite(inputThresh) ? inputThresh : -40;
  return { silences: await detectSilences(file, thresholdDb, minSeconds), thresholdDb };
}

/** Top-level MP4 boxes in file order, e.g. ["ftyp", "moov", "mdat"]. */
export function mp4TopLevelBoxes(file: string): string[] {
  const fd = openSync(file, "r");
  const size = statSync(file).size;
  const boxes: string[] = [];
  const header = Buffer.alloc(16);
  try {
    let offset = 0;
    while (offset + 8 <= size && boxes.length < 64) {
      readSync(fd, header, 0, 16, offset);
      let boxSize = header.readUInt32BE(0);
      const type = header.toString("latin1", 4, 8);
      if (boxSize === 1) boxSize = Number(header.readBigUInt64BE(8));
      if (boxSize === 0) boxSize = size - offset;
      if (boxSize < 8) break;
      boxes.push(type);
      offset += boxSize;
    }
  } finally {
    closeSync(fd);
  }
  return boxes;
}

/** Moves the MP4 index to the front so phones can start playing before the download ends. */
export async function ensureFaststart(file: string): Promise<boolean> {
  const boxes = mp4TopLevelBoxes(file);
  if (boxes.indexOf("moov") !== -1 && boxes.indexOf("moov") < boxes.indexOf("mdat")) return false;
  const temp = `${file}.faststart.mp4`;
  const result = await ffmpeg(["-y", "-i", file, "-map", "0", "-c", "copy", "-movflags", "+faststart", temp]);
  if (result.code !== 0) throw new Error(`Could not move the MP4 index to the front: ${result.stderr.slice(-400)}`);
  const { renameSync } = await import("node:fs");
  renameSync(temp, file);
  return true;
}
