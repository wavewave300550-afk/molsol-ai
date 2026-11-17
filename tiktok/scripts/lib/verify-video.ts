/**
 * Checks a rendered MP4 the way a phone and TikTok will see it, and that it
 * really follows the narration: same length plus the tail, speech starting
 * and ending where the narration does, nothing cut.
 */
import { existsSync, statSync } from "node:fs";
import type { Interval } from "../../src/lib/alignment.ts";
import { AUDIO_MASTER } from "../../src/lib/config.ts";
import type { Timeline } from "../../src/lib/timeline.ts";
import { detectPauses, ffmpeg, ffprobeJson, measureLoudness, mp4TopLevelBoxes } from "./ffmpeg.ts";
import type { EpisodePaths } from "./paths.ts";

export type Check = { name: string; pass: boolean; detail: string };
export type VideoReport = {
  file: string;
  episodeId: string;
  checkedAt: string;
  pass: boolean;
  checks: Check[];
  metrics: Record<string, number | string>;
};

const firstSpeech = (silences: Interval[]) => (silences[0] && silences[0].start <= 0.01 ? silences[0].end : 0);
const lastSpeech = (silences: Interval[], duration: number) => {
  const last = silences[silences.length - 1];
  return last && last.end >= duration - 0.05 ? last.start : duration;
};

export async function verifyVideo(paths: EpisodePaths, timeline: Timeline, file = paths.video): Promise<VideoReport> {
  const checks: Check[] = [];
  const metrics: VideoReport["metrics"] = {};
  const add = (name: string, pass: boolean, detail: string) => checks.push({ name, pass, detail });
  const finish = (): VideoReport => ({
    file,
    episodeId: timeline.episodeId,
    checkedAt: new Date().toISOString(),
    pass: checks.every((c) => c.pass),
    checks,
    metrics,
  });

  const exists = existsSync(file) && statSync(file).size > 0;
  add("MP4 file exists", exists, exists ? `${(statSync(file).size / 1e6).toFixed(1)} MB` : "missing");
  if (!exists) return finish();

  const probe = await ffprobeJson(file);
  const video = probe.streams.find((s) => s.codec_type === "video");
  const audio = probe.streams.find((s) => s.codec_type === "audio");
  const fps = timeline.fps;
  add("MP4 container", /mp4|mov/.test(probe.format.format_name), probe.format.format_name);
  add("H.264 video", video?.codec_name === "h264", `${video?.codec_name} (${video?.codec_tag_string}), ${video?.profile} profile, level ${video?.level}`);
  add("1080×1920 portrait", video?.width === 1080 && video?.height === 1920, `${video?.width}×${video?.height}`);
  add("30 fps", video?.r_frame_rate === "30/1" && video?.avg_frame_rate === "30/1", `${video?.r_frame_rate}, average ${video?.avg_frame_rate}`);
  add("yuv420p pixels (iPhone compatible)", video?.pix_fmt === "yuv420p", String(video?.pix_fmt));
  add("Frame count matches the timeline", Number(video?.nb_frames) === timeline.durationInFrames, `${video?.nb_frames} of ${timeline.durationInFrames} frames`);
  add("AAC audio", audio?.codec_name === "aac", `${audio?.codec_name}, ${audio?.sample_rate} Hz, ${audio?.channels} channel(s)`);

  const videoSeconds = Number(video?.duration ?? probe.format.duration);
  const expected = timeline.durationInFrames / fps;
  const narration = timeline.audio.durationSeconds;
  metrics.videoSeconds = videoSeconds;
  metrics.narrationSeconds = narration;
  metrics.tailSeconds = timeline.tailSeconds;
  add(
    "Length = narration + tail",
    Math.abs(videoSeconds - expected) <= 1 / fps + 0.001 && Math.abs(videoSeconds - (narration + timeline.tailSeconds)) <= 1 / fps + 0.001,
    `video ${videoSeconds.toFixed(3)} s = narration ${narration.toFixed(3)} s + tail ${timeline.tailSeconds} s (±1 frame)`,
  );
  const audioSeconds = Number(audio?.duration ?? 0);
  metrics.audioTrackSeconds = audioSeconds;
  add("Narration not cut", audioSeconds >= narration - 0.02, `audio track ${audioSeconds.toFixed(3)} s ≥ narration ${narration.toFixed(3)} s`);

  const boxes = mp4TopLevelBoxes(file);
  add("Fast start (index before media)", boxes.indexOf("moov") !== -1 && boxes.indexOf("moov") < boxes.indexOf("mdat"), boxes.join(" → "));

  // Decode every frame and sample (explicit codecs: Remotion's FFmpeg build
  // has no default encoder for the null output).
  const decode = await ffmpeg(["-v", "error", "-i", file, "-map", "0", "-c:v", "rawvideo", "-c:a", "pcm_s16le", "-f", "null", "-"]);
  add("Decodes start to end without errors", decode.code === 0 && decode.stderr.trim() === "", decode.stderr.trim().slice(0, 200) || "no decoder errors");

  const [inVideo, inNarration] = await Promise.all([detectPauses(file), detectPauses(paths.narrationWav)]);
  const startShift = firstSpeech(inVideo.silences) - firstSpeech(inNarration.silences);
  const endShift = lastSpeech(inVideo.silences, videoSeconds) - lastSpeech(inNarration.silences, narration);
  metrics.speechStartShiftMs = Math.round(startShift * 1000);
  metrics.speechEndShiftMs = Math.round(endShift * 1000);
  add(
    "Speech in the video lines up with the narration",
    Math.abs(startShift) <= 0.06 && Math.abs(endShift) <= 0.06,
    `first word ${(startShift * 1000).toFixed(0)} ms, last word ${(endShift * 1000).toFixed(0)} ms from the narration file`,
  );
  const loudness = await measureLoudness(file);
  metrics.loudnessLufs = loudness.inputI;
  metrics.truePeakDb = loudness.inputTp;
  add(
    "Loudness about -14 LUFS, no clipping",
    Math.abs(loudness.inputI - AUDIO_MASTER.integratedLufs) <= 1.5 && loudness.inputTp <= 0,
    `${loudness.inputI} LUFS (target ${AUDIO_MASTER.integratedLufs}), true peak ${loudness.inputTp} dBTP`,
  );
  return finish();
}

export function printReport(report: VideoReport): void {
  console.log(`\nVerification of ${report.file}`);
  for (const c of report.checks) console.log(`  ${c.pass ? "PASS" : "FAIL"}  ${c.name}: ${c.detail}`);
  if (report.metrics.loudnessLufs !== undefined) {
    console.log(`  info  Loudness ${report.metrics.loudnessLufs} LUFS, true peak ${report.metrics.truePeakDb} dBTP`);
  }
  console.log(report.pass ? "\n✔ All checks passed." : "\n✖ Some checks failed.");
}
