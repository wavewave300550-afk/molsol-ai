/**
 * Starts a new episode script from the template.
 *
 * Usage: npm run new-episode -- <episode-id> ["Thai title"]
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { ok, runCli } from "./lib/cli.ts";
import { episodePaths, projectRoot } from "./lib/paths.ts";

runCli(() => {
  const paths = episodePaths(process.argv[2]);
  if (existsSync(paths.episodeFile)) throw new Error(`episodes/${paths.id}/episode.json already exists.`);
  const template = JSON.parse(readFileSync(join(projectRoot, "episodes", "_template", "episode.json"), "utf8"));
  template.id = paths.id;
  if (process.argv[3]) template.title = process.argv[3];
  mkdirSync(paths.episodeDir, { recursive: true });
  writeFileSync(paths.episodeFile, `${JSON.stringify(template, null, 2)}\n`);
  ok(`Created episodes/${paths.id}/episode.json. Write the script, then: npm run validate -- ${paths.id}`);
});
