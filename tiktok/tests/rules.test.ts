import assert from "node:assert/strict";
import { test } from "node:test";
import { hasErrors } from "../src/lib/issues.ts";
import { findForbiddenEndings, findProfanity, validateEpisode } from "../src/lib/rules.ts";
import { makeEpisode, pipelineTestEpisode } from "./helpers.ts";

const particles = (text: string) => findForbiddenEndings(text).map((f) => f.particle);

test("sentence-final ครับ, ค่ะ and คะ are rejected", () => {
  assert.deepEqual(particles("วันนี้อากาศดีครับ"), ["ครับ"]);
  assert.deepEqual(particles("ขอบคุณนะคะ"), ["คะ"]);
  assert.deepEqual(particles("สวัสดีค่ะ วันนี้เรามาดูน้ำกัน"), ["ค่ะ"]);
  assert.deepEqual(particles("ไปด้วยกันครับๆ"), ["ครับ"]);
  assert.deepEqual(particles("ครับ!"), ["ครับ"]);
  // No space after the particle: it still ends the utterance.
  assert.deepEqual(particles("ได้ครับวันนี้เรามาดูกัน"), ["ครับ"]);
  assert.deepEqual(particles("เห็นไหมคะ ทุกอย่างเริ่มจากอะตอม"), ["คะ"]);
});

test("words that merely contain the particle letters pass", () => {
  assert.deepEqual(particles("คะแนนสอบวิทยาศาสตร์สูงขึ้น"), []);
  assert.deepEqual(particles("น้ำประกอบด้วยไฮโดรเจนและออกซิเจน"), []);
  assert.deepEqual(particles("ระบบเรนเดอร์เป็นวิดีโอ"), []);
});

test("profanity is matched on Thai words, not substrings", () => {
  assert.deepEqual(findProfanity("มึงทำอะไรอยู่").blocked, ["มึง"]);
  assert.deepEqual(findProfanity("ค้นหาในกูเกิลได้ทันที").blocked, []);
  assert.deepEqual(findProfanity("เปิดหีบสมบัติ").blocked, []);
  assert.deepEqual(findProfanity("แม่งานของงานนี้").blocked, []);
  assert.deepEqual(findProfanity("ตัวเหี้ยว่ายน้ำ").blocked, ["เหี้ย"]);
  assert.deepEqual(findProfanity("โอ๊ย ชิบหายแล้ว").blocked, ["ชิบหาย"]);
  assert.deepEqual(findProfanity("ช่วงเป็นสัดของโค").review, ["สัด"]);
  assert.deepEqual(findProfanity("this is shit").blocked, ["shit"]);
  assert.deepEqual(findProfanity("shiitake and shitake mushrooms").blocked, []);
});

test("the pipeline-test episode has no errors", () => {
  const issues = validateEpisode(pipelineTestEpisode(), { publicFileExists: () => true });
  assert.equal(hasErrors(issues), false, JSON.stringify(issues, null, 2));
});

test("script errors are reported with stable codes", () => {
  const base = makeEpisode();
  const codes = (episode: ReturnType<typeof makeEpisode>) => validateEpisode(episode).map((i) => i.code);
  assert.deepEqual(codes(base).filter((c) => !c.startsWith("ESTIMATE_")), []);

  const scenes = structuredClone(base.scenes);
  scenes[1].narration = "น้ำหนึ่งโมเลกุลมีสองอะตอมครับ";
  scenes[1].sourceIds = [];
  const broken = makeEpisode({ scenes });
  const found = codes(broken);
  for (const code of ["POLITE_ENDING", "CUE_NOT_IN_NARRATION", "FACT_WITHOUT_SOURCE", "UNUSED_SOURCE"]) {
    assert.ok(found.includes(code), `${code} missing from ${found.join(", ")}`);
  }

  const noCard = makeEpisode({ scenes: base.scenes.slice(0, 2) });
  assert.ok(codes(noCard).includes("SOURCES_CARD_MISSING"));
  const complex = makeEpisode({ durationTier: "complex" });
  assert.ok(codes(complex).includes("COMPLEX_WITHOUT_REASON"));
});
