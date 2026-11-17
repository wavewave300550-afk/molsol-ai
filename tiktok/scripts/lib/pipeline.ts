/**
 * The production steps after narration exists: build the timeline from the
 * narration, render the MP4, write the TikTok description with sources.
 */
import { existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { AlignmentFile } from "../../src/lib/alignment.ts";
import { checkVideoDuration, formatSeconds } from "../../src/lib/duration.ts";
import { formatIssues, hasErrors } from "../../src/lib/issues.ts";
import { validateEpisode } from "../../src/lib/rules.ts";
import type { Episode } from "../../src/lib/schema.ts";
import { buildTimeline, type Timeline } from "../../src/lib/timeline.ts";
import { approvalStatus, narrationHash } from "./approval.ts";
import { ok, step } from "./cli.ts";
import { type LoadedEpisode, loadEpisode, publicFileExists, readJson, writeJson } from "./episode-io.ts";
import { audioDurationSeconds, ensureFaststart, run } from "./ffmpeg.ts";
import { readNarrationMeta } from "./narration.ts";
import { type EpisodePaths, ensureDir, projectRoot } from "./paths.ts";

export const isTestRender = (timeline: Timeline): boolean =>
  timeline.kind === "pipeline-test" || timeline.audio.narrationSource === "test-audio";

export type BuiltEpisode = LoadedEpisode & { timeline: Timeline };

/**
 * Builds public/episodes/<id>/timeline.json. Refuses when the script has
 * errors, the narration belongs to another version of the script, a real
 * episode is not approved, or the result does not fit the duration tier.
 */
export async function buildEpisodeTimeline(id: string | undefined): Promise<BuiltEpisode> {
  const loaded = loadEpisode(id);
  const { episode, paths } = loaded;
  const issues = validateEpisode(episode, { publicFileExists });
  if (hasErrors(issues)) throw new Error(`The script has errors:\n${formatIssues(issues)}`);

  const meta = readNarrationMeta(paths);
  if (!meta || !existsSync(paths.narrationWav) || !existsSync(paths.alignment)) {
    throw new Error(
      `No narration for "${paths.id}" yet. Make it with: npm run narrate -- ${paths.id} (ElevenLabs), ` +
        `npm run audio:import -- ${paths.id} <file> (a recording), or test everything with: npm run pipeline:test`,
    );
  }
  if (meta.narrationHash !== narrationHash(episode)) {
    throw new Error("The narration was made for an earlier version of the script. Generate the narration again.");
  }
  if (episode.kind === "episode" && meta.source !== "test-audio") {
    const status = approvalStatus(episode);
    if (!status.approved) throw new Error(`Cannot build a production timeline: ${status.reason}`);
  }

  const alignment = readJson<AlignmentFile>(paths.alignment);
  const measured = await audioDurationSeconds(paths.narrationWav);
  if (Math.abs(measured - alignment.audioDurationSeconds) > 0.05) {
    throw new Error(`narration.wav lasts ${measured} s but its timing is for ${alignment.audioDurationSeconds} s. Prepare the narration again.`);
  }
  const timeline = buildTimeline({
    episode,
    alignment,
    audioDurationSeconds: measured,
    audioSrc: `${paths.mediaStaticDir}/narration.wav`,
    narrationHash: meta.narrationHash,
    narrationSource: meta.source,
  });
  const lengthIssues = checkVideoDuration(timeline.durationSeconds, episode);
  if (hasErrors(lengthIssues)) throw new Error(formatIssues(lengthIssues));
  writeJson(paths.timeline, timeline);

  ok(
    `Timeline: ${timeline.scenes.length} scenes, ${timeline.durationInFrames} frames = ${formatSeconds(timeline.durationSeconds)} ` +
      `(narration ${formatSeconds(measured)} + ${timeline.tailSeconds} s tail, timing: ${timeline.audio.timingSource})`,
  );
  for (const s of timeline.scenes) {
    const start = formatSeconds(s.from / timeline.fps).padStart(8);
    const end = formatSeconds((s.from + s.durationInFrames) / timeline.fps).padStart(8);
    console.log(`   ${String(s.index + 1).padStart(2)}. ${s.id.padEnd(14)} ${start} → ${end}  ${s.captions.length} subtitle pages, ${Object.keys(s.cues).length} cues`);
  }
  if (lengthIssues.length) console.log(formatIssues(lengthIssues));
  return { ...loaded, timeline };
}

export async function renderEpisode(id: string | undefined): Promise<BuiltEpisode> {
  const built = await buildEpisodeTimeline(id);
  const { paths, timeline, episode } = built;
  ensureDir(paths.outDir);
  const propsFile = join(paths.outDir, `${paths.id}.props.json`);
  writeJson(propsFile, { episodeId: paths.id });

  const args = ["render", "src/index.ts", "Episode", paths.video, `--props=${propsFile}`];
  const licenseKey = process.env.REMOTION_LICENSE_KEY?.trim();
  if (licenseKey) {
    args.push(`--license-key=${licenseKey}`);
    if (isTestRender(timeline)) args.push("--is-production=false");
  }
  step(`Rendering ${paths.id}: ${timeline.durationInFrames} frames, 1080×1920, 30 fps, H.264`);
  // Behind an HTTPS proxy (Claude Code cloud sessions), Node only uses it for
  // Remotion's one-time browser download when NODE_USE_ENV_PROXY is set.
  const env = process.env.HTTPS_PROXY && !process.env.NODE_USE_ENV_PROXY ? { ...process.env, NODE_USE_ENV_PROXY: "1" } : process.env;
  const result = await run(join(projectRoot, "node_modules", ".bin", "remotion"), args, { inherit: true, env });
  if (result.code !== 0) throw new Error("Remotion render failed (see the log above).");
  if (await ensureFaststart(paths.video)) ok("Moved the MP4 index to the front so phones can stream it");
  writeDescription(episode, timeline, paths);
  ok(`Rendered ${paths.video}`);
  return built;
}

/** Text to paste into the TikTok description, with the sources. */
export function writeDescription(episode: Episode, timeline: Timeline, paths: EpisodePaths): void {
  const lines = [episode.title, ""];
  if (isTestRender(timeline)) lines.push("[ทดสอบระบบ ไม่ใช่ตอนจริง ห้ามเผยแพร่]", "");
  if (episode.sources.length) {
    lines.push("แหล่งอ้างอิง");
    episode.sources.forEach((s, i) => {
      const link = s.doi ? `https://doi.org/${s.doi}` : (s.url ?? "");
      lines.push(`${i + 1}. ${s.citation}${link ? ` ${link}` : ""}`);
    });
  }
  writeFileSync(paths.description, `${lines.join("\n")}\n`);
}
