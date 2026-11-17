import { readFileSync } from "node:fs";
import { join } from "node:path";
import { type Episode, EpisodeSchema } from "../src/lib/schema.ts";
import { projectRoot } from "../scripts/lib/paths.ts";

export function pipelineTestEpisode(): Episode {
  const raw = JSON.parse(readFileSync(join(projectRoot, "episodes", "pipeline-test", "episode.json"), "utf8"));
  return EpisodeSchema.parse(raw);
}

/** A small valid "episode" kind script; override fields per test. */
export function makeEpisode(overrides: Record<string, unknown> = {}): Episode {
  return EpisodeSchema.parse({
    schemaVersion: 1,
    id: "unit-test",
    kind: "episode",
    title: "ตอนทดสอบ",
    language: "th",
    durationTier: "standard",
    sources: [
      { id: "src", label: "แหล่ง", citation: "ผู้แต่ง (2020). ชื่อเรื่อง.", url: "https://example.org/a", accessed: "2026-01-01" },
    ],
    scenes: [
      { id: "hook", label: "เปิด", factual: false, narration: "น้ำคือสารที่สำคัญที่สุดอย่างหนึ่งของโลก", visual: { type: "title", title: "น้ำ" } },
      {
        id: "fact",
        label: "ข้อเท็จจริง",
        narration: "น้ำหนึ่งโมเลกุลมีไฮโดรเจนสองอะตอม",
        sourceIds: ["src"],
        cues: [{ id: "h", text: "ไฮโดรเจน" }],
        visual: { type: "fact", title: "อะตอม", items: [{ value: 2, label: "ไฮโดรเจน", cue: "h" }] },
      },
      { id: "sources", label: "อ้างอิง", factual: false, narration: "ข้อมูลมาจากแหล่งที่แสดงบนจอ", visual: { type: "sources", title: "อ้างอิง" } },
    ],
    approval: null,
    ...overrides,
  });
}
