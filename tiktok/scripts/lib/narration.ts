/**
 * Turning a narration audio file into the files the timeline is built from:
 *   public/episodes/<id>/narration.wav   playback copy (mastered, 48 kHz)
 *   public/episodes/<id>/alignment.json  character timing for the script
 *   public/episodes/<id>/narration.json  where the narration came from
 */
import { copyFileSync, existsSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import type { AlignmentFile, AlignmentSource, CharacterAlignment } from "../../src/lib/alignment.ts";
import { estimateAlignmentFromSilences, mapAlignmentToText, normalizeAlignment } from "../../src/lib/alignment.ts";
import { TIMELINE, VIDEO } from "../../src/lib/config.ts";
import { checkVideoDuration, formatSeconds } from "../../src/lib/duration.ts";
import { formatIssues } from "../../src/lib/issues.ts";
import { fullNarration } from "../../src/lib/rules.ts";
import type { Episode } from "../../src/lib/schema.ts";
import { narrationHash } from "./approval.ts";
import { ok, warn } from "./cli.ts";
import { readJson, writeJson } from "./episode-io.ts";
import { detectPauses, masterNarration } from "./ffmpeg.ts";
import { type EpisodePaths, ensureDir } from "./paths.ts";

export type NarrationMeta = {
  version: 1;
  source: "elevenlabs" | "local-file" | "test-audio";
  narrationHash: string;
  sourceFile: string;
  durationSeconds: number;
  masterGainDb: number;
  timingSource: AlignmentSource;
  voiceId?: string;
  modelId?: string;
  requestId?: string | null;
  characterCount?: string | null;
  createdAt: string;
};

export type PrepareInput = {
  episode: Episode;
  paths: EpisodePaths;
  sourceFile: string;
  source: NarrationMeta["source"];
  /** Exact timing (from ElevenLabs or a file); estimated from pauses if missing. */
  alignment?: CharacterAlignment | null;
  timingSource?: AlignmentSource;
  extra?: Partial<NarrationMeta>;
};

export async function prepareNarration(input: PrepareInput): Promise<{ meta: NarrationMeta; alignment: AlignmentFile }> {
  const { episode, paths } = input;
  ensureDir(paths.mediaDir);
  const text = fullNarration(episode.scenes);
  const hash = narrationHash(episode);

  const master = await masterNarration(input.sourceFile, paths.narrationWav);
  ok(`Mastered narration: ${formatSeconds(master.outputSeconds)}, gain ${master.gainDb.toFixed(1)} dB (length unchanged)`);

  let characterAlignment = input.alignment ?? null;
  let timingSource: AlignmentSource = input.timingSource ?? "elevenlabs";
  if (characterAlignment) {
    const match = mapAlignmentToText(text, characterAlignment).matchRatio;
    if (match < 0.9) {
      warn(`Only ${(match * 100).toFixed(0)}% of the timing matches the script; estimating timing from pauses instead.`);
      characterAlignment = null;
    }
  }
  if (!characterAlignment) {
    const { silences, thresholdDb } = await detectPauses(paths.narrationWav);
    characterAlignment = estimateAlignmentFromSilences(text, silences, master.outputSeconds);
    timingSource = "estimated-from-silences";
    ok(`Estimated word timing from ${silences.length} pauses (threshold ${thresholdDb.toFixed(1)} dB)`);
  }

  const alignment: AlignmentFile = {
    version: 1,
    source: timingSource,
    text,
    narrationHash: hash,
    audioDurationSeconds: master.outputSeconds,
    alignment: characterAlignment,
    createdAt: new Date().toISOString(),
  };
  const meta: NarrationMeta = {
    version: 1,
    source: input.source,
    narrationHash: hash,
    sourceFile: input.sourceFile.split("/").pop() ?? input.sourceFile,
    durationSeconds: master.outputSeconds,
    masterGainDb: Number(master.gainDb.toFixed(2)),
    timingSource,
    createdAt: alignment.createdAt,
    ...input.extra,
  };
  writeJson(paths.alignment, alignment);
  writeJson(paths.narrationMeta, meta);
  reportLength(episode, master.outputSeconds);
  return { meta, alignment };
}

/** Tells right away whether this narration fits the episode's duration tier. */
export function reportLength(episode: Episode, audioSeconds: number): void {
  const videoSeconds = Math.ceil((audioSeconds + TIMELINE.tailSeconds) * VIDEO.fps) / VIDEO.fps;
  const issues = checkVideoDuration(videoSeconds, episode);
  if (issues.length === 0) ok(`Video will be ${formatSeconds(videoSeconds)}: fits the "${episode.durationTier}" tier.`);
  else warn(`Video will be ${formatSeconds(videoSeconds)}:\n${formatIssues(issues)}`);
}

export function readNarrationMeta(paths: EpisodePaths): NarrationMeta | null {
  return existsSync(paths.narrationMeta) ? readJson<NarrationMeta>(paths.narrationMeta) : null;
}

/**
 * Uses an existing audio file as the narration (a recording, or the
 * temporary test audio). Timing comes from a timing file if given, else it
 * is estimated from the pauses with FFmpeg.
 */
export async function importAudio(input: {
  episode: Episode;
  paths: EpisodePaths;
  file: string;
  test: boolean;
  timingFile?: string;
}): Promise<{ meta: NarrationMeta; alignment: AlignmentFile }> {
  const { episode, paths, file } = input;
  if (!existsSync(file)) throw new Error(`Audio file not found: ${file}`);
  ensureDir(paths.mediaDir);
  const stored = join(paths.mediaDir, `narration.source${extname(file) || ".audio"}`);
  if (resolve(file) !== resolve(stored)) copyFileSync(file, stored);

  let alignment: CharacterAlignment | null = null;
  let timingSource: AlignmentSource | undefined;
  if (input.timingFile) {
    const raw = readJson<Record<string, unknown>>(input.timingFile);
    alignment = normalizeAlignment(raw.alignment ?? raw);
    if (!alignment) throw new Error(`${input.timingFile} is not a character timing file.`);
    timingSource = (raw.source as AlignmentSource | undefined) ?? "elevenlabs";
  }
  return prepareNarration({
    episode,
    paths,
    sourceFile: stored,
    source: input.test ? "test-audio" : "local-file",
    alignment,
    timingSource,
  });
}
