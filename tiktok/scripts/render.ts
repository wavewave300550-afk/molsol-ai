/**
 * Renders an episode to out/<id>.mp4 (1080×1920, 30 fps, H.264 + AAC) from
 * its narration, then verifies the file. Also writes out/<id>.description.txt
 * (title + sources for the TikTok description) and out/<id>.report.json.
 *
 * Usage: npm run render -- <episode-id>
 */
import { runCli } from "./lib/cli.ts";
import { writeJson } from "./lib/episode-io.ts";
import { renderEpisode } from "./lib/pipeline.ts";
import { printReport, verifyVideo } from "./lib/verify-video.ts";

runCli(async () => {
  const { paths, timeline } = await renderEpisode(process.argv[2]);
  const report = await verifyVideo(paths, timeline);
  writeJson(paths.report, report);
  printReport(report);
  if (!report.pass) throw new Error(`The video failed verification; see ${paths.report}`);
});
