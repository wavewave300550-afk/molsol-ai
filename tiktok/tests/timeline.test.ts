import assert from "node:assert/strict";
import { test } from "node:test";
import { type AlignmentFile, estimateAlignmentFromSilences, mapAlignmentToText, normalizeAlignment } from "../src/lib/alignment.ts";
import { CAPTIONS, TIMELINE } from "../src/lib/config.ts";
import { NO_BREAK_AFTER } from "../src/lib/glossary.ts";
import { fullNarration } from "../src/lib/rules.ts";
import type { Episode } from "../src/lib/schema.ts";
import { normalizeNarration, stripTrailingNonWord, visibleLength } from "../src/lib/text.ts";
import { buildTimeline } from "../src/lib/timeline.ts";
import { narrationHash } from "../scripts/lib/approval.ts";
import { planSyntheticNarration } from "../scripts/lib/test-audio.ts";
import { pipelineTestEpisode } from "./helpers.ts";

const FPS = 30;

function sceneStarts(episode: Episode): number[] {
  const starts: number[] = [];
  let offset = 0;
  episode.scenes.forEach((scene, i) => {
    if (i > 0) starts.push(offset);
    offset += normalizeNarration(scene.narration).length + 1;
  });
  return starts;
}

function fixture(extraSilenceSeconds = 0, alignmentOverride?: AlignmentFile["alignment"]) {
  const episode = pipelineTestEpisode();
  const text = fullNarration(episode.scenes);
  const plan = planSyntheticNarration(text, sceneStarts(episode));
  const audioDurationSeconds = plan.durationSeconds + extraSilenceSeconds;
  const alignment: AlignmentFile = {
    version: 1,
    source: "synthetic-test",
    text,
    narrationHash: narrationHash(episode),
    audioDurationSeconds,
    alignment: alignmentOverride ?? plan.alignment,
    createdAt: "2026-11-17T00:00:00.000Z",
  };
  const timeline = buildTimeline({
    episode,
    alignment,
    audioDurationSeconds,
    audioSrc: "episodes/pipeline-test/narration.wav",
    narrationHash: narrationHash(episode),
  });
  return { episode, text, plan, timeline };
}

test("the video lasts as long as the audio plus the tail, never less", () => {
  const a = fixture();
  const b = fixture(3);
  assert.equal(a.timeline.durationInFrames, Math.ceil((a.plan.durationSeconds + TIMELINE.tailSeconds) * FPS));
  assert.ok(a.timeline.durationInFrames / FPS >= a.plan.durationSeconds);
  const extra = b.timeline.durationInFrames - a.timeline.durationInFrames;
  assert.ok(Math.abs(extra - 3 * FPS) <= 1, `3 s more audio gave ${extra} more frames`);
});

test("scenes tile the whole video and cut in just before their first word", () => {
  const { timeline } = fixture();
  const scenes = timeline.scenes;
  assert.equal(scenes[0].from, 0);
  scenes.forEach((scene, i) => {
    const end = scene.from + scene.durationInFrames;
    assert.equal(end, i + 1 < scenes.length ? scenes[i + 1].from : timeline.durationInFrames);
    if (i > 0) {
      assert.ok(scene.from / FPS <= scene.speechStartSeconds + 0.5 / FPS, `${scene.id} starts after its first word`);
      assert.ok(scene.from / FPS >= scenes[i - 1].speechEndSeconds - 0.5 / FPS, `${scene.id} cuts off the previous scene`);
    }
  });
});

test("cues fire on the frame their words are spoken", () => {
  const { episode, plan, timeline } = fixture();
  let offset = 0;
  episode.scenes.forEach((scene, i) => {
    const narration = normalizeNarration(scene.narration);
    for (const cue of scene.cues) {
      const at = offset + narration.indexOf(cue.text);
      const expected = Math.round(plan.alignment.character_start_times_seconds[at] * FPS);
      assert.equal(timeline.scenes[i].from + timeline.scenes[i].cues[cue.id], expected, `cue ${scene.id}/${cue.id}`);
    }
    offset += narration.length + 1;
  });
});

test("subtitles are the narration word for word, in order, and readable", () => {
  const { episode, timeline } = fixture();
  timeline.scenes.forEach((scene, i) => {
    const shown = scene.captions.map((p) => p.text).join("").replace(/\s/g, "");
    assert.equal(shown, normalizeNarration(episode.scenes[i].narration).replace(/\s/g, ""), `scene ${scene.id}`);
    scene.captions.forEach((page, p) => {
      assert.ok(page.startMs < page.endMs, `page ${p} of ${scene.id} has no duration`);
      if (p + 1 < scene.captions.length) assert.ok(page.endMs <= scene.captions[p + 1].startMs, "pages overlap");
      if (page.tokens.length > 1) assert.ok(visibleLength(page.text) <= CAPTIONS.maxChars, `page too long: ${page.text}`);
      assert.ok(page.tokens[0].startMs >= page.startMs);
      assert.equal(page.tokens[page.tokens.length - 1].pageBreakAfter, true);
    });
    const last = scene.captions[scene.captions.length - 1];
    assert.ok(last.endMs <= (scene.durationInFrames / FPS) * 1000 + 1, "subtitle outlives its scene");
  });
});

test("science terms stay whole and pages do not end on a lead-in word", () => {
  const { timeline } = fixture();
  const pages = timeline.scenes.flatMap((s) => s.captions.map((p) => p.text));
  for (const term of ["เบนซีน", "แนฟทาลีน", "ไพรีน", "โปรเจกต์", "ไฮโดรเจน", "ออกซิเจน"]) {
    assert.ok(pages.some((p) => p.includes(term)), `"${term}" was split across pages: ${pages.join(" | ")}`);
  }
  for (const page of timeline.scenes.flatMap((s) => s.captions)) {
    const last = stripTrailingNonWord(page.tokens[page.tokens.length - 1].text.trim());
    assert.ok(!NO_BREAK_AFTER.has(last), `page ends with lead-in word "${last}": ${page.text}`);
  }
});

test("timing estimated from pauses alone stays close to the real timing", () => {
  const exact = fixture();
  const { plan, text } = exact;
  const silences = [{ start: 0, end: plan.words[0].start }];
  plan.words.forEach((word, i) => {
    const next = plan.words[i + 1];
    if (next && next.start - word.end >= 0.18) silences.push({ start: word.end, end: next.start });
  });
  silences.push({ start: plan.words[plan.words.length - 1].end, end: plan.durationSeconds });
  const estimated = fixture(0, estimateAlignmentFromSilences(text, silences, plan.durationSeconds));
  estimated.timeline.scenes.forEach((scene, i) => {
    const truth = exact.timeline.scenes[i];
    assert.ok(Math.abs(scene.from - truth.from) <= 3, `${scene.id}: ${scene.from} vs ${truth.from}`);
    for (const [id, frame] of Object.entries(truth.cues)) {
      assert.ok(Math.abs(scene.from + scene.cues[id] - (truth.from + frame)) <= 6, `cue ${scene.id}/${id}`);
    }
  });
});

test("alignment with missing or extra whitespace still lines up", () => {
  const text = "น้ำ คือ ชีวิต";
  const spoken = Array.from("น้ำคือ\nชีวิต");
  const timing = mapAlignmentToText(text, {
    characters: spoken,
    character_start_times_seconds: spoken.map((_, i) => i * 0.1),
    character_end_times_seconds: spoken.map((_, i) => i * 0.1 + 0.1),
  });
  assert.equal(timing.matchRatio, 1);
  for (let i = 1; i < text.length; i++) assert.ok(timing.start[i] >= timing.start[i - 1]);
});

test("the WebSocket alignment format is accepted", () => {
  const converted = normalizeAlignment({ chars: ["ก"], charStartTimesMs: [100], charDurationsMs: [50] });
  assert.deepEqual(converted?.characters, ["ก"]);
  assert.ok(Math.abs((converted?.character_start_times_seconds[0] ?? 0) - 0.1) < 1e-9);
  assert.ok(Math.abs((converted?.character_end_times_seconds[0] ?? 0) - 0.15) < 1e-9);
  assert.equal(normalizeAlignment({ unexpected: true }), null);
});

test("editing the script after narration is detected", () => {
  const { plan, text } = fixture();
  const episode = pipelineTestEpisode();
  episode.scenes[0].narration += " เพิ่ม";
  assert.throws(
    () =>
      buildTimeline({
        episode,
        alignment: { version: 1, source: "synthetic-test", text, narrationHash: "x", audioDurationSeconds: plan.durationSeconds, alignment: plan.alignment, createdAt: "" },
        audioDurationSeconds: plan.durationSeconds,
        audioSrc: "x",
        narrationHash: "x",
      }),
    /different script/,
  );
});
