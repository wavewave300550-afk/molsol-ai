/**
 * Verifies a rendered episode MP4 against its timeline and narration.
 *
 * Usage: npm run verify -- <episode-id> [--file path/to/video.mp4]
 */
import { existsSync } from "node:fs";
import { parseArgs } from "node:util";
import type { Timeline } from "../src/lib/timeline.ts";
import { runCli } from "./lib/cli.ts";
import { readJson, writeJson } from "./lib/episode-io.ts";
import { episodePaths } from "./lib/paths.ts";
import { printReport, verifyVideo } from "./lib/verify-video.ts";

runCli(async () => {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: { file: { type: "string" } } });
  const paths = episodePaths(positionals[0]);
  if (!existsSync(paths.timeline)) throw new Error(`No timeline for ${paths.id}. Render it first: npm run render -- ${paths.id}`);
  const report = await verifyVideo(paths, readJson<Timeline>(paths.timeline), values.file ?? paths.video);
  writeJson(paths.report, report);
  printReport(report);
  if (!report.pass) throw new Error("Verification failed.");
});
