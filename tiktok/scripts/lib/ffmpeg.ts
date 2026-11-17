/**
 * FFmpeg and FFprobe helpers. They use the binaries that ship with Remotion
 * (`remotion ffmpeg` / `remotion ffprobe`), so nothing extra is installed
 * locally or in CI. Set FFMPEG_BIN / FFPROBE_BIN to use other binaries.
 */
import { spawn } from "node:child_process";
import { closeSync, openSync, readSync, statSync } from "node:fs";
import { join } from "node:path";
import type { Interval } from "../../src/lib/alignment.ts";
import { AUDIO_MASTER } from "../../src/lib/config.ts";
import { projectRoot } from "./paths.ts";

const remotionBin = join(projectRoot, "node_modules", ".bin", "remotion");

function tool(name: "ffmpeg" | "ffprobe"): { cmd: string; pre: string[] } {
  const override = process.env[name === "ffmpeg" ? "FFMPEG_BIN" : "FFPROBE_BIN"];
  return override ? { cmd: override, pre: [] } : { cmd: remotionBin, pre: [name] };
}

export type RunResult = { code: number; stdout: string; stderr: string };

export function run(cmd: string, args: string[], options: { cwd?: string; inherit?: boolean } = {}): Promise<RunResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: options.cwd ?? projectRoot,
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
  sample_rate?: string;
  channels?: number;
};
export type FfprobeResult = { streams: FfprobeStream[]; format: { format_name: string; duration: string; size: string; bit_rate?: string } };

export async function audioDurationSeconds(file: string): Promise<number> {
  const probe = await ffprobeJson(file);
  const audio = probe.streams.find((s) => s.codec_type === "audio");
  if (!audio) throw new Error(`${file} has no audio stream.`);
  return Number(audio.duration ?? probe.format.duration);
}

export type Loudness = { inputI: number; inputTp: number; inputLra: number; inputThresh: number };

/** EBU R128 loudness of the first audio stream (FFmpeg loudnorm analysis). */
export async function measureLoudness(file: string): Promise<Loudness> {
  const { integratedLufs: I, truePeakDb: TP, loudnessRange: LRA } = AUDIO_MASTER;
  const result = await ffmpeg(["-i", file, "-map", "0:a:0", "-af", `loudnorm=I=${I}:TP=${TP}:LRA=${LRA}:print_format=json`, "-f", "null", "-"]);
  const json = result.stderr.slice(result.stderr.lastIndexOf("{"), result.stderr.lastIndexOf("}") + 1);
  if (result.code !== 0 || !json) throw new Error(`Loudness analysis failed for ${file}: ${result.stderr.slice(-400)}`);
  const m = JSON.parse(json) as Record<string, string>;
  return { inputI: Number(m.input_i), inputTp: Number(m.input_tp), inputLra: Number(m.input_lra), inputThresh: Number(m.input_thresh) };
}

export type MasterResult = { gainDb: number; inputSeconds: number; outputSeconds: number; loudness: Loudness };

/**
 * Makes the playback copy of the narration: one constant gain toward
 * -14 LUFS (capped so it never clips) and 48 kHz mono. A constant gain and
 * resampling leave timing and dynamics untouched; the output must be as long
 * as the input or the step fails.
 */
export async function masterNarration(input: string, output: string): Promise<MasterResult> {
  const loudness = await measureLoudness(input);
  if (!Number.isFinite(loudness.inputI) || loudness.inputI < -70) throw new Error(`${input} is silent; there is no narration to use.`);
  const gainDb = Math.min(AUDIO_MASTER.integratedLufs - loudness.inputI, AUDIO_MASTER.truePeakDb - loudness.inputTp);
  const result = await ffmpeg([
    "-y",
    "-i",
    input,
    "-map",
    "0:a:0",
    "-af",
    `volume=${gainDb.toFixed(2)}dB,aresample=${AUDIO_MASTER.sampleRate}`,
    "-ac",
    "1",
    "-c:a",
    "pcm_s16le",
    output,
  ]);
  if (result.code !== 0) throw new Error(`Could not master ${input}: ${result.stderr.slice(-400)}`);
  const inputSeconds = await audioDurationSeconds(input);
  const outputSeconds = await audioDurationSeconds(output);
  if (Math.abs(inputSeconds - outputSeconds) > 0.01) {
    throw new Error(`Mastering changed the narration length (${inputSeconds} s -> ${outputSeconds} s). Nothing may shorten narration.`);
  }
  return { gainDb, inputSeconds, outputSeconds, loudness };
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
