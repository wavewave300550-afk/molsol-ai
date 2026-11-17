/**
 * Prints the verification report of a render as Markdown (for the GitHub
 * Actions run summary).
 *
 * Usage: node scripts/summary.ts <episode-id> [narration-mode]
 */
import { existsSync } from "node:fs";
import { readJson } from "./lib/episode-io.ts";
import { episodePaths } from "./lib/paths.ts";
import type { VideoReport } from "./lib/verify-video.ts";

const paths = episodePaths(process.argv[2]);
const lines = [`## ${paths.id}`, "", `Narration: \`${process.argv[3] ?? "?"}\``, ""];
if (existsSync(paths.report)) {
  const report = readJson<VideoReport>(paths.report);
  lines.push(report.pass ? "**All checks passed.**" : "**Some checks failed.**", "", "| Check | Result | Detail |", "| --- | --- | --- |");
  for (const c of report.checks) lines.push(`| ${c.name} | ${c.pass ? "✅ PASS" : "❌ FAIL"} | ${c.detail.replace(/\|/g, "\\|").replace(/\n/g, " ")} |`);
} else {
  lines.push("No verification report (the render did not finish).");
}
console.log(lines.join("\n"));
