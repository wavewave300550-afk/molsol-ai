/**
 * Uses an existing audio file as an episode's narration: a recording, or
 * temporary test audio. Needs no ElevenLabs key; timing is estimated from
 * the pauses (or read from --timing).
 *
 * Usage: npm run audio:import -- <episode-id> <audio-file> [--timing timing.json] [--test]
 *   --test  mark it as temporary test audio: the video gets a TEST badge and
 *           the script does not need approval yet.
 */
import { parseArgs } from "node:util";
import { formatIssues, hasErrors } from "../src/lib/issues.ts";
import { validateEpisode } from "../src/lib/rules.ts";
import { approvalStatus } from "./lib/approval.ts";
import { ok, runCli } from "./lib/cli.ts";
import { loadEpisode, publicFileExists } from "./lib/episode-io.ts";
import { importAudio } from "./lib/narration.ts";

runCli(async () => {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: { timing: { type: "string" }, test: { type: "boolean", default: false } },
  });
  const { episode, paths } = loadEpisode(positionals[0]);
  if (!positionals[1]) throw new Error("Give the audio file: npm run audio:import -- <episode-id> <audio-file>");
  const issues = validateEpisode(episode, { publicFileExists });
  if (hasErrors(issues)) throw new Error(`The script has errors:\n${formatIssues(issues)}`);
  const test = values.test || episode.kind === "pipeline-test";
  if (!test) {
    const status = approvalStatus(episode);
    if (!status.approved) throw new Error(`Narration is only accepted for an approved script. ${status.reason}`);
  }
  await importAudio({ episode, paths, file: positionals[1], test, timingFile: values.timing });
  ok(`Narration ready${test ? " (test audio)" : ""}. Next: npm run render -- ${episode.id}`);
});
