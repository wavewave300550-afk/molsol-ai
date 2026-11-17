import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { type Episode, EpisodeSchema, formatSchemaError } from "../../src/lib/schema.ts";
import { episodePaths, type EpisodePaths, projectRoot } from "./paths.ts";

export type LoadedEpisode = { episode: Episode; raw: Record<string, unknown>; paths: EpisodePaths };

export function loadEpisode(id: string | undefined): LoadedEpisode {
  const paths = episodePaths(id);
  if (!existsSync(paths.episodeFile)) {
    throw new Error(`No script at episodes/${paths.id}/episode.json. Create one with: npm run new-episode -- ${paths.id}`);
  }
  let raw: Record<string, unknown>;
  try {
    raw = JSON.parse(readFileSync(paths.episodeFile, "utf8"));
  } catch (error) {
    throw new Error(`episodes/${paths.id}/episode.json is not valid JSON: ${(error as Error).message}`);
  }
  const parsed = EpisodeSchema.safeParse(raw);
  if (!parsed.success) {
    throw new Error(`episodes/${paths.id}/episode.json does not match the script format:\n${formatSchemaError(parsed.error)}`);
  }
  if (parsed.data.id !== paths.id) {
    throw new Error(`episode.json says id "${parsed.data.id}" but lives in episodes/${paths.id}/. They must match.`);
  }
  return { episode: parsed.data, raw, paths };
}

/** Writes the raw JSON back, keeping the author's fields as they wrote them. */
export function saveRawEpisode(paths: EpisodePaths, raw: Record<string, unknown>): void {
  writeFileSync(paths.episodeFile, `${JSON.stringify(raw, null, 2)}\n`);
}

export const publicFileExists = (path: string): boolean => existsSync(join(projectRoot, "public", path));

export function readJson<T>(path: string): T {
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

export function writeJson(path: string, value: unknown): void {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}
