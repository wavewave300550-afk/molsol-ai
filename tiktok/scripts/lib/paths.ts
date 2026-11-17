import { existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/** The tiktok/ project folder, wherever the script is started from. */
export const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

const EPISODE_ID = /^[a-z0-9][a-z0-9-]{1,63}$/;

export function assertEpisodeId(id: string | undefined): string {
  if (!id || !EPISODE_ID.test(id)) {
    throw new Error(
      `Episode id must be lowercase letters, digits and hyphens (got ${JSON.stringify(id)}). ` +
        "Example: npm run validate -- ep001-water",
    );
  }
  return id;
}

export type EpisodePaths = {
  id: string;
  episodeDir: string;
  episodeFile: string;
  /** public/episodes/<id>/ — served to Remotion through staticFile(). */
  mediaDir: string;
  /** Path of the media folder relative to public/, for staticFile(). */
  mediaStaticDir: string;
  narrationSource: string;
  narrationWav: string;
  narrationMeta: string;
  alignment: string;
  timeline: string;
  outDir: string;
  video: string;
  report: string;
  description: string;
};

export function episodePaths(rawId: string | undefined): EpisodePaths {
  const id = assertEpisodeId(rawId);
  const episodeDir = join(projectRoot, "episodes", id);
  const mediaDir = join(projectRoot, "public", "episodes", id);
  const outDir = join(projectRoot, "out");
  return {
    id,
    episodeDir,
    episodeFile: join(episodeDir, "episode.json"),
    mediaDir,
    mediaStaticDir: `episodes/${id}`,
    narrationSource: join(mediaDir, "narration.source.mp3"),
    narrationWav: join(mediaDir, "narration.wav"),
    narrationMeta: join(mediaDir, "narration.json"),
    alignment: join(mediaDir, "alignment.json"),
    timeline: join(mediaDir, "timeline.json"),
    outDir,
    video: join(outDir, `${id}.mp4`),
    report: join(outDir, `${id}.report.json`),
    description: join(outDir, `${id}.description.txt`),
  };
}

export function ensureDir(path: string): string {
  if (!existsSync(path)) mkdirSync(path, { recursive: true });
  return path;
}
