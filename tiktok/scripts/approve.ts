/**
 * Records that a person reviewed the scientific script and approves it for
 * narration. Run it only after checking every claim against its source.
 *
 * Usage: npm run approve -- <episode-id> --by "Reviewer name" [--note "..."]
 *
 * The approval stores a hash of the script. Any later edit to narration,
 * visuals, sources or the duration tier voids it and narration is refused
 * until the script is approved again.
 */
import { parseArgs } from "node:util";
import { formatIssues, hasErrors } from "../src/lib/issues.ts";
import { validateEpisode } from "../src/lib/rules.ts";
import { approvalStatus, contentHash } from "./lib/approval.ts";
import { ok, runCli } from "./lib/cli.ts";
import { loadEpisode, publicFileExists, saveRawEpisode } from "./lib/episode-io.ts";

runCli(() => {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: { by: { type: "string" }, note: { type: "string" } },
  });
  const { episode, raw, paths } = loadEpisode(positionals[0]);
  if (!values.by?.trim()) throw new Error('Say who approves: npm run approve -- <episode-id> --by "Your name"');

  const issues = validateEpisode(episode, { publicFileExists });
  if (hasErrors(issues)) throw new Error(`Cannot approve a script with errors:\n${formatIssues(issues)}`);
  if (approvalStatus(episode).approved) {
    ok(`Already approved by ${episode.approval?.approvedBy}; nothing changed.`);
    return;
  }

  const warnings = issues.filter((i) => i.level === "warning");
  console.log("Before approving, the reviewer confirms that:");
  console.log("  • every factual sentence matches its cited source;");
  console.log("  • numbers, units and on-screen labels match the narration;");
  console.log("  • the narration is polite, has no profanity and no sentence-final ครับ/ค่ะ/คะ;");
  if (episode.durationTier === "complex") console.log(`  • 90-120 s is necessary: ${episode.complexJustification}`);
  if (warnings.length) console.log(`\nOpen warnings (approving accepts them):\n${formatIssues(warnings)}`);

  raw.approval = {
    approvedBy: values.by.trim(),
    approvedAt: new Date().toISOString(),
    contentHash: contentHash(episode),
    durationTier: episode.durationTier,
    ...(values.note ? { notes: values.note } : {}),
  };
  saveRawEpisode(paths, raw);
  ok(`Approved episodes/${episode.id}/episode.json for narration. Commit the file to record the approval.`);
});
