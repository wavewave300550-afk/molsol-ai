/**
 * Narrator voice tests (episodes with "kind": "voice-test").
 *
 *   npm run voice-test -- <id>            check the test can be narrated and show what it
 *                                         will send and cost. Sends nothing, no credits.
 *   npm run voice-test -- <id> --report   after `npm run narrate -- <id>`: check the take
 *                                         (ElevenLabs timing, length, loudness) and write
 *                                         out/<id>.voice-report.json. No credits.
 *
 * Narration itself is the normal `npm run narrate -- <id>` (approval required).
 * On GitHub: Actions > Voice test > Run workflow.
 */
import { appendFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";
import type { AlignmentFile } from "../src/lib/alignment.ts";
import { TIMELINE, TTS, VOICE_TEST } from "../src/lib/config.ts";
import { estimateVideoSeconds, formatSeconds } from "../src/lib/duration.ts";
import { formatIssues, hasErrors } from "../src/lib/issues.ts";
import { fullNarration, validateEpisode } from "../src/lib/rules.ts";
import { approvalStatus } from "./lib/approval.ts";
import { ok, runCli } from "./lib/cli.ts";
import { loadEpisode, publicFileExists, readJson, writeJson } from "./lib/episode-io.ts";
import { audioDurationSeconds, measureLoudness } from "./lib/ffmpeg.ts";
import { readNarrationMeta } from "./lib/narration.ts";
import { ensureDir } from "./lib/paths.ts";
import { describeVoice, resolveVoice } from "./lib/voice.ts";
import { buildVoiceTestReport, formatVoiceTestReport } from "./lib/voice-test.ts";

const summary = (title: string, lines: string[]) => {
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, `## ${title}\n\n${lines.map((l) => `- ${l}`).join("\n")}\n\n`);
};

runCli(async () => {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: { report: { type: "boolean", default: false } } });
  const { episode, paths } = loadEpisode(positionals[0]);
  if (episode.kind !== "voice-test") {
    throw new Error(`"${episode.id}" is a ${episode.kind}, not a voice test. Episodes are narrated and rendered through the TikTok render workflow.`);
  }

  if (!values.report) {
    const issues = validateEpisode(episode, { publicFileExists });
    const status = approvalStatus(episode);
    const voice = resolveVoice({ env: process.env.ELEVENLABS_VOICE_ID, episode: episode.voice?.voiceId });
    const characters = fullNarration(episode.scenes).length;
    const lines = [
      `Voice: ${describeVoice(voice)}, from ${voice.source}`,
      `Model: ${episode.voice?.modelId ?? TTS.modelId}, language ${TTS.languageCode}`,
      `Text: ${characters} characters (at most ${VOICE_TEST.maxCharacters} for a voice test)`,
      `Expected cost: about ${characters} ElevenLabs credits at 1 credit per character; the exact count comes back with the audio`,
      `Estimated length: ${formatSeconds(estimateVideoSeconds(episode.scenes) - TIMELINE.tailSeconds)} (allowed ${VOICE_TEST.minSeconds}-${VOICE_TEST.maxSeconds} s)`,
      `Script: ${hasErrors(issues) ? "has errors" : status.approved ? `approved by ${episode.approval?.approvedBy} on ${episode.approval?.approvedAt}` : "not approved yet"}`,
    ];
    for (const line of lines) console.log(line);
    summary(`Voice test plan: ${episode.id}`, lines);
    if (hasErrors(issues)) throw new Error(`The voice test script has errors:\n${formatIssues(issues)}`);
    if (!status.approved) {
      throw new Error(`${status.reason}\n  Approve the test script first (npm run approve -- ${episode.id} --by "Name") and commit the file.`);
    }
    ok("Ready to narrate. Nothing was sent and no credits were used.");
    return;
  }

  const meta = readNarrationMeta(paths);
  if (!meta || !existsSync(paths.alignment) || !existsSync(paths.narrationWav)) {
    throw new Error(`No narration for ${episode.id} yet. Run: npm run narrate -- ${episode.id}`);
  }
  const alignment = readJson<AlignmentFile>(paths.alignment);
  const [sourceSeconds, masteredSeconds, loudness] = await Promise.all([
    audioDurationSeconds(join(paths.mediaDir, meta.sourceFile)),
    audioDurationSeconds(paths.narrationWav),
    measureLoudness(paths.narrationWav),
  ]);
  const report = buildVoiceTestReport(episode, meta, alignment, {
    sourceSeconds,
    masteredSeconds,
    loudnessLufs: loudness.inputI,
    truePeakDb: loudness.inputTp,
  });
  const reportFile = join(ensureDir(paths.outDir), `${episode.id}.voice-report.json`);
  writeJson(reportFile, report);
  const lines = formatVoiceTestReport(report);
  console.log(`\nVoice test ${episode.id}`);
  for (const line of lines) console.log(`  ${line}`);
  summary(`Voice test result: ${report.pass ? "passed" : "failed"}`, lines);
  if (!report.pass) throw new Error(`The voice test failed some checks; see ${reportFile}`);
  ok(`All checks passed. Report: ${reportFile}`);
});
