/**
 * Checks an episode script: format, Thai narration rules (no profanity, no
 * sentence-final ครับ/ค่ะ/คะ), sources, cues, duration estimate, approval.
 *
 * Usage: npm run validate -- <episode-id>
 * Exit code 1 when there are errors.
 */
import { estimateVideoSeconds, formatSeconds } from "../src/lib/duration.ts";
import { formatIssues, hasErrors } from "../src/lib/issues.ts";
import { fullNarration, validateEpisode } from "../src/lib/rules.ts";
import { approvalStatus } from "./lib/approval.ts";
import { runCli } from "./lib/cli.ts";
import { loadEpisode, publicFileExists } from "./lib/episode-io.ts";

runCli(() => {
  const { episode } = loadEpisode(process.argv[2]);
  const issues = validateEpisode(episode, { publicFileExists });
  const status = approvalStatus(episode);

  console.log(`Episode: ${episode.id} — ${episode.title} (${episode.kind}, ${episode.durationTier} tier)`);
  console.log(`Scenes: ${episode.scenes.length}, sources: ${episode.sources.length}, narration: ${fullNarration(episode.scenes).length} characters`);
  console.log(`Estimated length: ${formatSeconds(estimateVideoSeconds(episode.scenes))} (only an estimate; the narration decides)`);
  console.log(`Approval: ${status.approved ? `approved by ${episode.approval?.approvedBy} on ${episode.approval?.approvedAt}` : status.reason}`);
  console.log(`\nIssues:\n${formatIssues(issues)}`);

  if (hasErrors(issues)) throw new Error("The script has errors. Fix them before approval or narration.");
  console.log("\n✔ No errors.");
});
