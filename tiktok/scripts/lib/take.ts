/**
 * A raw ElevenLabs take, saved the moment it arrives and before anything
 * else happens to it: the MP3 (narration.source.mp3) and, next to it,
 * elevenlabs-take.json with the character timing and request details that
 * only exist in that one response. If a later step fails (mastering, a
 * crash, a cancelled run), the take is prepared again from these files
 * instead of being paid for twice: `npm run narrate` reuses a saved take for
 * the same script, voice and model, and `npm run narration:recover` takes one
 * from anywhere (e.g. a GitHub Actions artifact).
 */
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { basename } from "node:path";
import { type CharacterAlignment, normalizeAlignment } from "../../src/lib/alignment.ts";
import { readJson, writeJson } from "./episode-io.ts";
import type { EpisodePaths } from "./paths.ts";

export type SavedTake = {
  version: 1;
  episodeId: string;
  /** Hash of the narration text it was made from (approval.ts). */
  narrationHash: string;
  text: string;
  voiceId: string;
  modelId: string;
  languageCode?: string;
  outputFormat?: string;
  requestId: string | null;
  characterCount: string | null;
  /** File name of the audio, and its SHA-256: the timing belongs to exactly this file. */
  audioFile: string;
  audioSha256: string;
  audioBytes: number;
  alignment: CharacterAlignment | null;
  normalizedAlignment: CharacterAlignment | null;
  createdAt: string;
};

export const sha256 = (data: Buffer): string => createHash("sha256").update(data).digest("hex");

export function saveTake(
  paths: EpisodePaths,
  audioFile: string,
  audio: Buffer,
  details: Omit<SavedTake, "version" | "episodeId" | "audioFile" | "audioSha256" | "audioBytes" | "createdAt">,
): SavedTake {
  const take: SavedTake = {
    version: 1,
    episodeId: paths.id,
    ...details,
    audioFile: basename(audioFile),
    audioSha256: sha256(audio),
    audioBytes: audio.length,
    createdAt: new Date().toISOString(),
  };
  writeJson(paths.elevenlabsTake, take);
  return take;
}

export function readSavedTake(file: string): SavedTake {
  const raw = readJson<Record<string, unknown>>(file);
  const text = (key: string) => typeof raw[key] === "string" && (raw[key] as string).length > 0;
  if (raw.version !== 1 || !text("narrationHash") || !text("voiceId") || !text("modelId") || !/^[0-9a-f]{64}$/.test(String(raw.audioSha256))) {
    throw new Error(`${file} is not a saved ElevenLabs take (elevenlabs-take.json).`);
  }
  return {
    ...(raw as unknown as SavedTake),
    alignment: normalizeAlignment(raw.alignment),
    normalizedAlignment: normalizeAlignment(raw.normalizedAlignment),
  };
}

/** Why a saved take cannot be used with this script and audio file; empty when it can. */
export function takeProblems(take: SavedTake, expected: { narrationHash: string; audioSha256: string }): string[] {
  const problems: string[] = [];
  if (take.narrationHash !== expected.narrationHash) problems.push("it was made for another version of the script");
  if (take.audioSha256 !== expected.audioSha256) problems.push("the audio file is not the one this take was saved with");
  return problems;
}

/**
 * The take saved in the episode's media folder, if it was made for this exact
 * script, voice and model and its MP3 is still the same file.
 */
export function findReusableTake(paths: EpisodePaths, want: { narrationHash: string; voiceId: string; modelId: string }): SavedTake | null {
  if (!existsSync(paths.elevenlabsTake) || !existsSync(paths.narrationSource)) return null;
  let take: SavedTake;
  try {
    take = readSavedTake(paths.elevenlabsTake);
  } catch {
    return null;
  }
  if (take.voiceId !== want.voiceId || take.modelId !== want.modelId) return null;
  const problems = takeProblems(take, { narrationHash: want.narrationHash, audioSha256: sha256(readFileSync(paths.narrationSource)) });
  return problems.length === 0 ? take : null;
}
