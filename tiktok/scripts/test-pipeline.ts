/**
 * End-to-end test of the production pipeline without an ElevenLabs key:
 * temporary test audio -> FFmpeg mastering and timing from pauses -> timeline
 * -> render -> verification that the MP4 plays and follows the test audio.
 *
 * Usage: npm run pipeline:test [-- <episode-id>]   (default: pipeline-test)
 * The video gets a TEST badge and must never be published.
 */
import { join } from "node:path";
import { formatSeconds } from "../src/lib/duration.ts";
import { buildTimeline } from "../src/lib/timeline.ts";
import { ok, runCli, step } from "./lib/cli.ts";
import { loadEpisode, writeJson } from "./lib/episode-io.ts";
import { audioDurationSeconds } from "./lib/ffmpeg.ts";
import { importAudio } from "./lib/narration.ts";
import { ensureDir, projectRoot } from "./lib/paths.ts";
import { renderEpisode } from "./lib/pipeline.ts";
import { makeTestAudio } from "./lib/test-audio.ts";
import { printReport, verifyVideo } from "./lib/verify-video.ts";

runCli(async () => {
  const id = process.argv[2] ?? "pipeline-test";
  const { episode, paths } = loadEpisode(id);

  step("1/5 Making temporary test audio (no ElevenLabs key needed)");
  const wav = join(ensureDir(join(projectRoot, "tmp", "test-audio")), `${id}.wav`);
  const plan = makeTestAudio(episode, wav);
  const testSeconds = await audioDurationSeconds(wav);
  ok(`${wav}: ${formatSeconds(testSeconds)}`);

  step("2/5 Importing it like a recording (FFmpeg mastering, timing from pauses)");
  const { alignment } = await importAudio({ episode, paths, file: wav, test: true });

  step("3/5 Comparing the estimated timing with the known timing");
  const common = { episode, audioDurationSeconds: alignment.audioDurationSeconds, audioSrc: "", narrationHash: alignment.narrationHash };
  const exact = buildTimeline({ ...common, alignment: { ...alignment, source: "synthetic-test", alignment: plan.alignment } });
  const estimated = buildTimeline({ ...common, alignment });
  let worstScene = 0;
  let worstCue = 0;
  estimated.scenes.forEach((scene, i) => {
    const truth = exact.scenes[i];
    worstScene = Math.max(worstScene, Math.abs(scene.from - truth.from));
    for (const [cue, frame] of Object.entries(truth.cues)) {
      worstCue = Math.max(worstCue, Math.abs(scene.from + scene.cues[cue] - (truth.from + frame)));
    }
  });
  ok(`Scene cuts within ${worstScene} frames and cues within ${worstCue} frames of the true timing`);

  step("4/5 Rendering");
  const { timeline } = await renderEpisode(id);

  step("5/5 Verifying the MP4");
  const report = await verifyVideo(paths, timeline);
  const videoSeconds = Number(report.metrics.videoSeconds);
  report.checks.push(
    {
      name: "Length follows the test audio",
      pass: Math.abs(videoSeconds - (testSeconds + timeline.tailSeconds)) <= 1 / timeline.fps + 0.001,
      detail: `video ${videoSeconds.toFixed(3)} s = test audio ${testSeconds.toFixed(3)} s + ${timeline.tailSeconds} s tail`,
    },
    {
      name: "Timing from pauses matches the true timing",
      pass: worstScene <= 5 && worstCue <= 9,
      detail: `scene cuts ≤ ${worstScene} frames off, cues ≤ ${worstCue} frames off (limits 5 and 9)`,
    },
  );
  report.pass = report.checks.every((c) => c.pass);
  writeJson(paths.report, report);
  printReport(report);
  if (!report.pass) throw new Error(`The pipeline test failed; see ${paths.report}`);
  ok(`Test video: ${paths.video} (TEST badge, never publish)`);
});
