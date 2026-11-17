/**
 * Temporary test narration: a speech-like tone for every word, with real
 * pauses at spaces and between scenes, timed from the script text. It lets
 * the whole pipeline (audio -> timing -> scenes -> subtitles -> MP4) run
 * without an ElevenLabs key. It is not speech and never goes into an episode.
 */
import { writeFileSync } from "node:fs";
import type { CharacterAlignment } from "../../src/lib/alignment.ts";
import { fullNarration, sceneRanges } from "../../src/lib/rules.ts";
import type { Episode } from "../../src/lib/schema.ts";
import { segmentWords, speechWeight } from "../../src/lib/text.ts";

/** Writes test audio for an episode plus its exact timing (<wav>.timing.json). */
export function makeTestAudio(episode: Episode, wavPath: string): SyntheticPlan {
  const text = fullNarration(episode.scenes);
  const plan = planSyntheticNarration(
    text,
    sceneRanges(episode.scenes)
      .slice(1)
      .map((r) => r.from),
  );
  writeSyntheticWav(wavPath, plan);
  writeFileSync(
    `${wavPath}.timing.json`,
    `${JSON.stringify({ source: "synthetic-test", text, durationSeconds: plan.durationSeconds, alignment: plan.alignment })}\n`,
  );
  return plan;
}

export type SyntheticOptions = {
  /** Speaking weight per second (see speechWeight), roughly Thai TTS pace. */
  rate: number;
  wordGap: number;
  phrasePause: number;
  scenePause: number;
  leadIn: number;
  tail: number;
};

export const DEFAULT_SYNTHETIC: SyntheticOptions = {
  rate: 13,
  wordGap: 0.045,
  phrasePause: 0.32,
  scenePause: 0.8,
  leadIn: 0.35,
  tail: 0.45,
};

export type SyntheticPlan = {
  durationSeconds: number;
  /** Exact timing of every character, in the ElevenLabs alignment format. */
  alignment: CharacterAlignment;
  /** Voiced stretches (one per word) to synthesise. */
  words: Array<{ start: number; end: number }>;
};

/** `sceneStarts`: offsets in `text` where each scene after the first begins. */
export function planSyntheticNarration(text: string, sceneStarts: number[], o: SyntheticOptions = DEFAULT_SYNTHETIC): SyntheticPlan {
  const start = new Array<number>(text.length).fill(0);
  const end = new Array<number>(text.length).fill(0);
  const words: SyntheticPlan["words"] = [];
  const sceneBreaks = new Set(sceneStarts.map((s) => s - 1));
  let t = o.leadIn;
  for (const seg of segmentWords(text)) {
    const from = seg.index;
    const to = from + seg.text.length;
    if (/^\s+$/u.test(seg.text)) {
      const pause = sceneBreaks.has(from) ? o.scenePause : o.phrasePause;
      for (let i = from; i < to; i++) {
        start[i] = t;
        end[i] = t + pause;
      }
      t += pause;
      continue;
    }
    const weight = speechWeight(seg.text);
    if (!seg.isWordLike || weight === 0) {
      for (let i = from; i < to; i++) start[i] = end[i] = t;
      continue;
    }
    const duration = Math.max(0.14, weight / o.rate);
    let c = t;
    for (let i = from; i < to; i++) {
      const d = (duration * speechWeight(text[i])) / weight;
      start[i] = c;
      end[i] = c + d;
      c += d;
    }
    words.push({ start: t, end: t + duration });
    t += duration + o.wordGap;
  }
  return {
    durationSeconds: t + o.tail,
    alignment: {
      characters: Array.from({ length: text.length }, (_, i) => text[i]),
      character_start_times_seconds: start,
      character_end_times_seconds: end,
    },
    words,
  };
}

/** Writes the plan as a 48 kHz mono 16-bit WAV of vowel-like tones. */
export function writeSyntheticWav(path: string, plan: SyntheticPlan, sampleRate = 48000): void {
  const samples = Math.ceil(plan.durationSeconds * sampleRate);
  const pcm = new Int16Array(samples);
  plan.words.forEach((word, w) => {
    const f0 = 150 + 45 * Math.sin(w * 1.7) + 15 * Math.sin(w * 0.37);
    const first = Math.floor(word.start * sampleRate);
    const last = Math.min(samples, Math.ceil(word.end * sampleRate));
    const length = (last - first) / sampleRate;
    for (let n = first; n < last; n++) {
      const local = (n - first) / sampleRate;
      const attack = Math.min(1, local / 0.012);
      const release = Math.min(1, (length - local) / 0.025);
      const syllables = 0.6 + 0.4 * Math.sin(Math.PI * 5.5 * local) ** 2;
      const f = f0 * (1 - 0.08 * (local / length));
      let v = 0;
      for (let h = 1; h <= 6; h++) {
        const formant = Math.exp(-(((h * f - 600) / 450) ** 2)) + 0.5 * Math.exp(-(((h * f - 1700) / 600) ** 2));
        v += ((0.35 + formant) / h) * Math.sin(2 * Math.PI * h * f * (n / sampleRate));
      }
      pcm[n] = Math.round(Math.max(-1, Math.min(1, 0.26 * v * attack * release * syllables)) * 32767);
    }
  });

  const header = Buffer.alloc(44);
  header.write("RIFF", 0, "ascii");
  header.writeUInt32LE(36 + pcm.byteLength, 4);
  header.write("WAVEfmt ", 8, "ascii");
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20); // PCM
  header.writeUInt16LE(1, 22); // mono
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * 2, 28);
  header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34);
  header.write("data", 36, "ascii");
  header.writeUInt32LE(pcm.byteLength, 40);
  writeFileSync(path, Buffer.concat([header, Buffer.from(pcm.buffer)]));
}
