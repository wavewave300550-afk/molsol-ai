/**
 * Checks a narrator voice test take: was it really ElevenLabs with
 * Madame Scientia, did character timing come back and match the script,
 * is it the right length, loud enough, and untouched (never sped up or cut,
 * checked sample by sample). Pure function over measurements of files
 * already on disk: it spends no credits.
 */
import { type AlignmentFile, mapAlignmentToText } from "../../src/lib/alignment.ts";
import { AUDIO_MASTER, TIMELINE, TTS, VOICE_TEST } from "../../src/lib/config.ts";
import { checkVideoDuration, estimateVideoSeconds } from "../../src/lib/duration.ts";
import { fullNarration, sceneRanges } from "../../src/lib/rules.ts";
import type { Episode } from "../../src/lib/schema.ts";
import { narrationHash } from "./approval.ts";
import type { NarrationMeta } from "./narration.ts";
import { describeMaster, type MasterAssessment } from "./pcm.ts";
import type { Check } from "./verify-video.ts";

export type VoiceTestMeasurements = {
  /** Exact length of the file ElevenLabs returned: decoded samples, not the MP3 header's estimate. */
  sourceSeconds: number;
  /** Exact length of the mastered playback copy (narration.wav). */
  masteredSeconds: number;
  /** The sample-by-sample comparison of the two (checkMaster). */
  master?: MasterAssessment;
  loudnessLufs: number;
  truePeakDb: number;
};

export type VoiceTestReport = {
  episodeId: string;
  checkedAt: string;
  pass: boolean;
  checks: Check[];
  /** Known limits that do not fail the test, e.g. a recovered take without ElevenLabs timing. */
  warnings: Array<{ name: string; detail: string }>;
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
  const warnings: VoiceTestReport["warnings"] = [];
  const add = (name: string, pass: boolean, detail: string) => checks.push({ name, pass, detail });
  const text = fullNarration(episode.scenes);
  const timing = mapAlignmentToText(text, alignment.alignment);
  const isNarrator = meta.voiceId === TTS.narrator.voiceId;

  add("Narrated by ElevenLabs", meta.source === "elevenlabs", `source: ${meta.source}`);
  add(`Voice is ${TTS.narrator.name}`, isNarrator, `${meta.voiceId ?? "unknown"}${isNarrator ? "" : `, expected ${TTS.narrator.voiceId}`}`);
  add("Made from this exact script", meta.narrationHash === narrationHash(episode), meta.narrationHash === narrationHash(episode) ? "matches" : "the script changed after this take");
  if (alignment.source !== "elevenlabs" && meta.recovered) {
    // The timing came back with this take but was lost before it was saved;
    // getting it again means paying for a new take.
    warnings.push({
      name: "Character timing came from ElevenLabs",
      detail:
        `no: estimated from the pauses. The timing ElevenLabs sent with this take was not saved by ${meta.recovered.from}; ` +
        "subtitles follow the phrases closely but not every word. A new take would bring exact timing.",
    });
  } else {
    add("Character timing came from ElevenLabs", alignment.source === "elevenlabs", `timing source: ${alignment.source}`);
  }
  add(
    "Timing lines up with the script",
    timing.matchRatio >= 0.95,
    `${(timing.matchRatio * 100).toFixed(1)}% of characters matched (${alignment.source} timing)`,
  );
  const lengthIssues = checkVideoDuration(m.masteredSeconds + TIMELINE.tailSeconds, { ...episode, kind: "voice-test" });
  add(
    `Length within ${VOICE_TEST.minSeconds}-${VOICE_TEST.maxSeconds} s`,
    lengthIssues.length === 0,
    lengthIssues[0]?.message ?? `${m.masteredSeconds.toFixed(2)} s of narration`,
  );
  // Sample-accurate: the playback copy may never be shorter than the source,
  // and is longer only by rounding up to whole 48 kHz samples (or silence).
  const shorter = m.masteredSeconds < m.sourceSeconds - 1e-7;
  const longer = m.masteredSeconds - m.sourceSeconds > 0.01;
  const problems = m.master?.problems ?? [];
  add(
    "Nothing sped up or cut",
    !shorter && !longer && problems.length === 0,
    m.master
      ? `ElevenLabs file → playback copy: ${describeMaster(m.master)}${problems.length ? `. The copy ${problems.join("; ")}` : ""}`
      : `ElevenLabs file ${m.sourceSeconds.toFixed(6)} s, playback copy ${m.masteredSeconds.toFixed(6)} s` +
          (shorter ? " (shorter)" : longer ? " (longer)" : ""),
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
    warnings,
    facts: {
      voice: isNarrator ? `${TTS.narrator.name} (${meta.voiceId})` : (meta.voiceId ?? "unknown"),
      model: meta.modelId ?? "unknown",
      characters: text.length,
      charactersBilled: meta.characterCount ?? "unknown",
      narrationSeconds: Number(m.masteredSeconds.toFixed(3)),
      estimatedSeconds: Number(estimated.toFixed(2)),
      requestId: meta.requestId ?? "unknown",
      ...(meta.recovered ? { recoveredFrom: meta.recovered.from, audioSha256: meta.recovered.audioSha256 } : {}),
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
  for (const w of report.warnings ?? []) lines.push(`WARN  ${w.name}: ${w.detail}`);
  const f = report.facts;
  lines.push(
    `info  ${f.voice}, model ${f.model}`,
    `info  ${f.characters} characters sent, ${f.charactersBilled} billed`,
    `info  ${f.narrationSeconds} s spoken (the estimate was ${f.estimatedSeconds} s)`,
    `info  scenes: ${report.scenes.map((s) => `${s.id} ${s.startSeconds}-${s.endSeconds} s`).join(", ")}`,
  );
  if (f.recoveredFrom) lines.push(`info  recovered from ${f.recoveredFrom} without a new request (audio SHA-256 ${f.audioSha256})`);
  return lines;
}
