/**
 * Builds public/episodes/<id>/timeline.json from the script and the narration.
 * `npm run render` does this too; run it alone to check timing quickly.
 *
 * Usage: npm run timeline -- <episode-id>
 */
import { runCli } from "./lib/cli.ts";
import { buildEpisodeTimeline } from "./lib/pipeline.ts";

runCli(async () => {
  await buildEpisodeTimeline(process.argv[2]);
});
