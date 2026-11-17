/**
 * Writes temporary test audio for an episode (tones timed from its script,
 * real pauses at phrase and scene breaks) to tmp/test-audio/<id>.wav.
 *
 * Usage: npm run audio:test -- <episode-id>
 * Then:  npm run audio:import -- <episode-id> tmp/test-audio/<id>.wav --test
 */
import { join } from "node:path";
import { formatSeconds } from "../src/lib/duration.ts";
import { ok, runCli } from "./lib/cli.ts";
import { loadEpisode } from "./lib/episode-io.ts";
import { ensureDir, projectRoot } from "./lib/paths.ts";
import { makeTestAudio } from "./lib/test-audio.ts";

runCli(() => {
  const { episode, paths } = loadEpisode(process.argv[2]);
  const wav = join(ensureDir(join(projectRoot, "tmp", "test-audio")), `${paths.id}.wav`);
  const plan = makeTestAudio(episode, wav);
  ok(`Wrote ${wav} (${formatSeconds(plan.durationSeconds)}, ${plan.words.length} words) and its exact timing ${wav}.timing.json`);
});
