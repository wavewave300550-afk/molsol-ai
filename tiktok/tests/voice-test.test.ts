import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import type { AlignmentFile } from "../src/lib/alignment.ts";
import { TTS } from "../src/lib/config.ts";
import { checkVideoDuration } from "../src/lib/duration.ts";
import { fullNarration, sceneRanges, validateEpisode } from "../src/lib/rules.ts";
import { type Episode, EpisodeSchema } from "../src/lib/schema.ts";
import type { Timeline } from "../src/lib/timeline.ts";
import { narrationHash } from "../scripts/lib/approval.ts";
import type { NarrationMeta } from "../scripts/lib/narration.ts";
import { projectRoot } from "../scripts/lib/paths.ts";
import { isTestRender } from "../scripts/lib/pipeline.ts";
import { planSyntheticNarration } from "../scripts/lib/test-audio.ts";
import { assessMaster } from "../scripts/lib/pcm.ts";
import { loudnessCheck } from "../scripts/lib/verify-video.ts";
import { buildVoiceTestReport, formatVoiceTestReport } from "../scripts/lib/voice-test.ts";

const voiceTestRaw = () => JSON.parse(readFileSync(join(projectRoot, "episodes", "voice-test", "episode.json"), "utf8"));
const voiceTest = (): Episode => EpisodeSchema.parse(voiceTestRaw());
const codes = (episode: Episode) => validateEpisode(episode, { publicFileExists: () => true }).map((i) => i.code);

test("voice tests have their own 5-30 s limits; episode tiers are unchanged", () => {
  const check = (seconds: number, kind?: Episode["kind"]) =>
    checkVideoDuration(seconds, { durationTier: "standard", ...(kind ? { kind } : {}) }).map((i) => i.code);
  assert.deepEqual(check(18.7, "voice-test"), []);
  assert.deepEqual(check(4, "voice-test"), ["VOICE_TEST_TOO_SHORT"]);
  assert.deepEqual(check(31, "voice-test"), ["VOICE_TEST_TOO_LONG"]);
  // The same 18.7 s is still rejected for everything that is not a voice test.
  assert.deepEqual(check(18.7), ["DURATION_UNDER_MIN"]);
  assert.deepEqual(check(18.7, "episode"), ["DURATION_UNDER_MIN"]);
  assert.deepEqual(check(18.7, "pipeline-test"), ["DURATION_UNDER_MIN"]);
  assert.deepEqual(check(75, "episode"), []);
});

test("the voice-test script passes without episode-only rules", () => {
  const found = codes(voiceTest());
  assert.ok(!found.some((c) => ["SOURCES_CARD_MISSING", "NO_TITLE_SCENE"].includes(c) || c.startsWith("ESTIMATE_")), found.join(", "));
  assert.deepEqual(validateEpisode(voiceTest(), { publicFileExists: () => true }).filter((i) => i.level === "error"), []);
});

test("the same short script as a real episode still gets every episode rule", () => {
  const asEpisode = EpisodeSchema.parse({ ...voiceTestRaw(), kind: "episode" });
  const issues = validateEpisode(asEpisode, { publicFileExists: () => true });
  assert.ok(issues.some((i) => i.code === "SOURCES_CARD_MISSING" && i.level === "error"));
  assert.ok(issues.some((i) => i.code === "ESTIMATE_DURATION_UNDER_MIN"));
});

test("voice tests keep the narration rules and a text cap", () => {
  const raw = voiceTestRaw();
  raw.scenes[0].narration = "สวัสดีครับ นี่คือการทดสอบเสียง";
  raw.scenes[1].sourceIds = [];
  const found = codes(EpisodeSchema.parse(raw));
  assert.ok(found.includes("POLITE_ENDING"));
  assert.ok(found.includes("FACT_WITHOUT_SOURCE"));

  const long = voiceTestRaw();
  long.scenes[2].narration = "ทดสอบเสียงบรรยาย ".repeat(30);
  assert.ok(codes(EpisodeSchema.parse(long)).includes("VOICE_TEST_TOO_MUCH_TEXT"));
});

test("voice tests and pipeline tests carry the TEST badge; real episodes do not", () => {
  const timeline = (kind: Episode["kind"]) => ({ kind, audio: { narrationSource: "elevenlabs" } }) as unknown as Timeline;
  assert.equal(isTestRender(timeline("voice-test")), true);
  assert.equal(isTestRender(timeline("pipeline-test")), true);
  assert.equal(isTestRender(timeline("episode")), false);
});

function take(overrides: { meta?: Partial<NarrationMeta>; alignment?: Partial<AlignmentFile> } = {}) {
  const episode = voiceTest();
  const text = fullNarration(episode.scenes);
  const plan = planSyntheticNarration(
    text,
    sceneRanges(episode.scenes)
      .slice(1)
      .map((r) => r.from),
  );
  const meta: NarrationMeta = {
    version: 1,
    source: "elevenlabs",
    narrationHash: narrationHash(episode),
    sourceFile: "narration.source.mp3",
    durationSeconds: plan.durationSeconds,
    masterGainDb: 0,
    timingSource: "elevenlabs",
    voiceId: TTS.narrator.voiceId,
    modelId: TTS.modelId,
    requestId: "test-request",
    characterCount: String(text.length),
    createdAt: "2026-11-17T00:00:00.000Z",
    ...overrides.meta,
  };
  const alignment: AlignmentFile = {
    version: 1,
    source: "elevenlabs",
    text,
    narrationHash: meta.narrationHash,
    audioDurationSeconds: plan.durationSeconds,
    alignment: plan.alignment,
    createdAt: meta.createdAt,
    ...overrides.alignment,
  };
  return { episode, meta, alignment, seconds: plan.durationSeconds };
}

test("a good take passes the voice-test report", () => {
  const { episode, meta, alignment, seconds } = take();
  const report = buildVoiceTestReport(episode, meta, alignment, { sourceSeconds: seconds, masteredSeconds: seconds, loudnessLufs: -14.1, truePeakDb: -4 });
  assert.equal(report.pass, true, JSON.stringify(report.checks, null, 1));
  assert.equal(report.facts.characters, 230);
  assert.deepEqual(
    report.scenes.map((s) => s.id),
    ["hello", "water", "check"],
  );
  assert.ok(report.scenes[1].startSeconds > report.scenes[0].endSeconds);
});

test("the report catches a wrong voice, missing timing, a cut and a bad length", () => {
  const failing = (overrides: Parameters<typeof take>[0], m: Partial<{ sourceSeconds: number; masteredSeconds: number }> = {}) => {
    const { episode, meta, alignment, seconds } = take(overrides);
    const report = buildVoiceTestReport(episode, meta, alignment, {
      sourceSeconds: m.sourceSeconds ?? seconds,
      masteredSeconds: m.masteredSeconds ?? seconds,
      loudnessLufs: -14,
      truePeakDb: -4,
    });
    return report.checks.filter((c) => !c.pass).map((c) => c.name);
  };
  assert.deepEqual(failing({ meta: { voiceId: "JBFqnCBsd6RMkjVDRZzb" } }), [`Voice is ${TTS.narrator.name}`]);
  assert.deepEqual(failing({ alignment: { source: "estimated-from-silences" } }), ["Character timing came from ElevenLabs"]);
  assert.deepEqual(failing({}, { masteredSeconds: 15 }), ["Nothing sped up or cut"]);
  assert.deepEqual(failing({}, { sourceSeconds: 40, masteredSeconds: 40 }), ["Length within 5-30 s"]);
});

test("the cut check is sample-accurate and uses decoded lengths, not the MP3 header", () => {
  const { episode, meta, alignment } = take();
  const report = (sourceSeconds: number, masteredSeconds: number) =>
    buildVoiceTestReport(episode, meta, alignment, { sourceSeconds, masteredSeconds, loudnessLufs: -14, truePeakDb: -4 }).checks.find(
      (c) => c.name === "Nothing sped up or cut",
    );
  // The failed take: 874,944 decoded samples at 44.1 kHz -> 952,320 at 48 kHz, both 19.84 s.
  // (Its MP3 header said 19.879184 s, which the old check compared and failed on.)
  assert.equal(report(874944 / 44100, 952320 / 48000)?.pass, true);
  assert.equal(report(874944 / 44100, 952319 / 48000)?.pass, false, "one sample short at 48 kHz");
  assert.equal(report(874944 / 44100, 952321 / 48000)?.pass, true, "rounding up by a sample is fine");
});

test("the report shows the sample counts and fails on any problem the master check found", () => {
  const { episode, meta, alignment } = take();
  const reference = new Float32Array(48000).map((_, i) => 0.3 * Math.sin(i / 7));
  const good = assessMaster({ sourceSamples: 44100, sourceRate: 44100, reference, master: reference, masterRate: 48000 });
  const cut = assessMaster({ sourceSamples: 44100, sourceRate: 44100, reference, master: reference.subarray(0, 47000), masterRate: 48000 });
  const check = (master: typeof good) =>
    buildVoiceTestReport(episode, meta, alignment, { sourceSeconds: 1, masteredSeconds: master.masterSamples / 48000, master, loudnessLufs: -14, truePeakDb: -4 }).checks.find(
      (c) => c.name === "Nothing sped up or cut",
    );
  assert.equal(check(good)?.pass, true);
  assert.match(check(good)?.detail ?? "", /44,100 samples at 44\.1 kHz → 48,000 at 48 kHz/);
  assert.equal(check(cut)?.pass, false);
  assert.match(check(cut)?.detail ?? "", /1000 samples \(20\.8 ms\) shorter than the source/);
});

test("a recovered take without ElevenLabs timing passes with a warning; a normal take without it still fails", () => {
  const recovered = take({
    meta: { recovered: { from: "GitHub Actions run 44044487202", audioSha256: "f".repeat(64), at: "2026-11-17T00:00:00.000Z" }, timingSource: "estimated-from-silences" },
    alignment: { source: "estimated-from-silences" },
  });
  const m = { sourceSeconds: recovered.seconds, masteredSeconds: recovered.seconds, loudnessLufs: -14, truePeakDb: -4 };
  const report = buildVoiceTestReport(recovered.episode, recovered.meta, recovered.alignment, m);
  assert.equal(report.pass, true, JSON.stringify(report.checks, null, 1));
  assert.deepEqual(
    report.warnings.map((w) => w.name),
    ["Character timing came from ElevenLabs"],
  );
  assert.equal(report.facts.recoveredFrom, "GitHub Actions run 44044487202");
  const lines = formatVoiceTestReport(report);
  assert.ok(lines.some((l) => l.startsWith("WARN  Character timing came from ElevenLabs: no: estimated from the pauses")));
  assert.ok(lines.some((l) => l.includes("recovered from GitHub Actions run 44044487202 without a new request")));

  const normal = take({ alignment: { source: "estimated-from-silences" } });
  const failed = buildVoiceTestReport(normal.episode, normal.meta, normal.alignment, m);
  assert.equal(failed.pass, false);
  assert.deepEqual(failed.warnings, []);
});

test("loudness: -14 LUFS, or quieter only because the peaks reached the ceiling; never clipping", () => {
  const pass = (lufs: number, truePeak: number) => loudnessCheck(lufs, truePeak).pass;
  assert.equal(pass(-14.1, -4), true);
  // The recovered take: one constant gain of +3.42 dB brings its peaks to -1.5 dBTP at -16.43 LUFS.
  assert.equal(pass(-16.43, -1.5), true);
  assert.match(loudnessCheck(-16.43, -1.5).detail, /as loud as one constant gain can make it/);
  assert.equal(pass(-16.43, -4), false, "quiet with room left below the ceiling");
  assert.equal(pass(-21, -1.5), false, "quieter than -20 LUFS");
  assert.equal(pass(-12, -1.5), false, "too loud");
  assert.equal(pass(-14, 0.2), false, "clipping");
});
