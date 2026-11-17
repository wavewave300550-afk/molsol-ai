/**
 * Checks a narrator voice test take: was it really ElevenLabs with
 * Madame Scientia, did character timing come back and match the script,
 * is it the right length, loud enough, and untouched (never sped up or cut).
 * Pure function over files already on disk: it spends no credits.
 */
import { type AlignmentFile, mapAlignmentToText } from "../../src/lib/alignment.ts";
import { AUDIO_MASTER, TIMELINE, TTS, VOICE_TEST } from "../../src/lib/config.ts";
import { checkVideoDuration, estimateVideoSeconds } from "../../src/lib/duration.ts";
import { fullNarration, sceneRanges } from "../../src/lib/rules.ts";
import type { Episode } from "../../src/lib/schema.ts";
import { narrationHash } from "./approval.ts";
import type { NarrationMeta } from "./narration.ts";
import type { Check } from "./verify-video.ts";

export type VoiceTestMeasurements = {
  /** Length of the file ElevenLabs returned. */
  sourceSeconds: number;
  /** Length of the mastered playback copy (narration.wav). */
  masteredSeconds: number;
  loudnessLufs: number;
  truePeakDb: number;
};

export type VoiceTestReport = {
  episodeId: string;
  checkedAt: string;
  pass: boolean;
  checks: Check[];
  facts: Record<string, string | number>;
  scenes: Array<{ id: string; startSeconds: number; endSeconds: number }>;
};

export function buildVoiceTestReport(
  episode: Episode,
  meta: NarrationMeta,
  alignment: AlignmentFile,
  m: VoiceTestMeasurements,
): VoiceTestReport {
  const checks: Check[] = [];
  const add = (name: string, pass: boolean, detail: string) => checks.push({ name, pass, detail });
  const text = fullNarration(episode.scenes);
  const timing = mapAlignmentToText(text, alignment.alignment);
  const isNarrator = meta.voiceId === TTS.narrator.voiceId;

  add("Narrated by ElevenLabs", meta.source === "elevenlabs", `source: ${meta.source}`);
  add(`Voice is ${TTS.narrator.name}`, isNarrator, `${meta.voiceId ?? "unknown"}${isNarrator ? "" : `, expected ${TTS.narrator.voiceId}`}`);
  add("Made from this exact script", meta.narrationHash === narrationHash(episode), meta.narrationHash === narrationHash(episode) ? "matches" : "the script changed after this take");
  add("Character timing came from ElevenLabs", alignment.source === "elevenlabs", `timing source: ${alignment.source}`);
  add("Timing lines up with the script", timing.matchRatio >= 0.95, `${(timing.matchRatio * 100).toFixed(1)}% of characters matched`);
  const lengthIssues = checkVideoDuration(m.masteredSeconds + TIMELINE.tailSeconds, { ...episode, kind: "voice-test" });
  add(
    `Length within ${VOICE_TEST.minSeconds}-${VOICE_TEST.maxSeconds} s`,
    lengthIssues.length === 0,
    lengthIssues[0]?.message ?? `${m.masteredSeconds.toFixed(2)} s of narration`,
  );
  add(
    "Nothing sped up or cut",
    Math.abs(m.sourceSeconds - m.masteredSeconds) <= 0.01,
    `ElevenLabs file ${m.sourceSeconds.toFixed(3)} s, playback copy ${m.masteredSeconds.toFixed(3)} s`,
  );
  add(
    `Loudness about ${AUDIO_MASTER.integratedLufs} LUFS, no clipping`,
    Math.abs(m.loudnessLufs - AUDIO_MASTER.integratedLufs) <= 1.5 && m.truePeakDb <= 0,
    `${m.loudnessLufs} LUFS, true peak ${m.truePeakDb} dBTP`,
  );

  const estimated = estimateVideoSeconds(episode.scenes) - TIMELINE.tailSeconds;
  return {
    episodeId: episode.id,
    checkedAt: new Date().toISOString(),
    pass: checks.every((c) => c.pass),
    checks,
    facts: {
      voice: isNarrator ? `${TTS.narrator.name} (${meta.voiceId})` : (meta.voiceId ?? "unknown"),
      model: meta.modelId ?? "unknown",
      characters: text.length,
      charactersBilled: meta.characterCount ?? "unknown",
      narrationSeconds: Number(m.masteredSeconds.toFixed(3)),
      estimatedSeconds: Number(estimated.toFixed(2)),
      requestId: meta.requestId ?? "unknown",
    },
    scenes: sceneRanges(episode.scenes).map((r, i) => ({
      id: episode.scenes[i].id,
      startSeconds: Number(timing.start[r.from].toFixed(2)),
      endSeconds: Number(timing.end[r.to - 1].toFixed(2)),
    })),
  };
}

export function formatVoiceTestReport(report: VoiceTestReport): string[] {
  const lines = report.checks.map((c) => `${c.pass ? "PASS" : "FAIL"}  ${c.name}: ${c.detail}`);
  const f = report.facts;
  lines.push(
    `info  ${f.voice}, model ${f.model}`,
    `info  ${f.characters} characters sent, ${f.charactersBilled} billed`,
    `info  ${f.narrationSeconds} s spoken (the estimate was ${f.estimatedSeconds} s)`,
    `info  scenes: ${report.scenes.map((s) => `${s.id} ${s.startSeconds}-${s.endSeconds} s`).join(", ")}`,
  );
  return lines;
}
