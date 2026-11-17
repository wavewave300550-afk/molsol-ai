import assert from "node:assert/strict";
import { test } from "node:test";
import { checkVideoDuration } from "../src/lib/duration.ts";
import { EpisodeSchema } from "../src/lib/schema.ts";
import { approvalStatus, canonicalJson, contentHash, narrationHash } from "../scripts/lib/approval.ts";
import { makeEpisode } from "./helpers.ts";

const approve = (episode: ReturnType<typeof makeEpisode>) =>
  EpisodeSchema.parse({
    ...episode,
    approval: {
      approvedBy: "Reviewer",
      approvedAt: "2026-11-17T09:00:00.000Z",
      contentHash: contentHash(episode),
      durationTier: episode.durationTier,
    },
  });

test("canonical JSON ignores key order", () => {
  assert.equal(canonicalJson({ b: 1, a: [{ d: 2, c: 3 }] }), canonicalJson({ a: [{ c: 3, d: 2 }], b: 1 }));
});

test("approval holds until the script changes", () => {
  const approved = approve(makeEpisode());
  assert.deepEqual(approvalStatus(approved), { approved: true });

  const edited = structuredClone(approved);
  edited.scenes[1].narration += " เพิ่มเติม";
  const status = approvalStatus(edited);
  assert.equal(status.approved, false);

  const visualEdit = structuredClone(approved);
  if (visualEdit.scenes[1].visual.type === "fact") visualEdit.scenes[1].visual.items[0].value = 3;
  assert.equal(approvalStatus(visualEdit).approved, false, "changing a number shown on screen voids approval");

  const voiceOnly = structuredClone(approved);
  voiceOnly.voice = { voiceId: "another-voice" };
  assert.equal(approvalStatus(voiceOnly).approved, true, "choosing a different voice keeps the approval");
});

test("unapproved and tier-mismatched scripts are refused", () => {
  assert.equal(approvalStatus(makeEpisode()).approved, false);
  const approved = approve(makeEpisode());
  const otherTier = structuredClone(approved);
  otherTier.durationTier = "complex";
  otherTier.complexJustification = "ต้องอธิบายหลายขั้นตอน";
  assert.equal(approvalStatus(otherTier).approved, false);
});

test("narration hash only follows the spoken words", () => {
  const a = makeEpisode();
  const b = structuredClone(a);
  if (b.scenes[1].visual.type === "fact") b.scenes[1].visual.items[0].value = 99;
  assert.equal(narrationHash(a), narrationHash(b));
  b.scenes[0].narration = "ข้อความใหม่";
  assert.notEqual(narrationHash(a), narrationHash(b));
});

test("duration tiers: 60-90 s standard, up to 120 s complex", () => {
  const standard = { durationTier: "standard" as const };
  const complex = { durationTier: "complex" as const, complexJustification: "เหตุผล" };
  const codes = (s: number, e: typeof standard | typeof complex) => checkVideoDuration(s, e).map((i) => i.code);
  assert.deepEqual(codes(59.9, standard), ["DURATION_UNDER_MIN"]);
  assert.deepEqual(codes(60, standard), []);
  assert.deepEqual(codes(90, standard), []);
  assert.deepEqual(codes(90.1, standard), ["DURATION_OVER_STANDARD"]);
  assert.deepEqual(codes(105, complex), []);
  assert.deepEqual(codes(120.01, complex), ["DURATION_OVER_MAX"]);
  assert.deepEqual(codes(80, complex), ["COMPLEX_NOT_NEEDED"]);
});
