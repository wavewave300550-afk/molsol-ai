/**
 * Character timing of the narration audio.
 *
 * ElevenLabs returns, for every character of the text it spoke, the time it
 * starts and ends. Everything visual (scene cuts, cues, subtitles) is placed
 * from these times, so the narration audio alone decides the timeline.
 * When only a plain audio file exists, the timing is estimated from its
 * pauses instead (estimateAlignmentFromSilences).
 */
import { speechWeight } from "./text.ts";

/** ElevenLabs REST "with-timestamps" alignment format. */
export type CharacterAlignment = {
  characters: string[];
  character_start_times_seconds: number[];
  character_end_times_seconds: number[];
};

export type AlignmentSource = "elevenlabs" | "estimated-from-silences" | "synthetic-test";

/** public/episodes/<id>/alignment.json */
export type AlignmentFile = {
  version: 1;
  source: AlignmentSource;
  /** Exactly the text that was spoken: scene narrations joined by single spaces. */
  text: string;
  narrationHash: string;
  audioDurationSeconds: number;
  alignment: CharacterAlignment;
  createdAt: string;
  notes?: string;
};

/**
 * Accepts the REST format and the WebSocket format
 * ({chars, charStartTimesMs, charDurationsMs}) and returns the REST format.
 */
export function normalizeAlignment(raw: unknown): CharacterAlignment | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  if (Array.isArray(r.characters) && Array.isArray(r.character_start_times_seconds) && Array.isArray(r.character_end_times_seconds)) {
    return {
      characters: r.characters.map(String),
      character_start_times_seconds: r.character_start_times_seconds.map(Number),
      character_end_times_seconds: r.character_end_times_seconds.map(Number),
    };
  }
  if (Array.isArray(r.chars) && Array.isArray(r.charStartTimesMs) && Array.isArray(r.charDurationsMs)) {
    const starts = r.charStartTimesMs.map((v) => Number(v) / 1000);
    return {
      characters: r.chars.map(String),
      character_start_times_seconds: starts,
      character_end_times_seconds: starts.map((s, i) => s + Number((r.charDurationsMs as unknown[])[i]) / 1000),
    };
  }
  return null;
}

export type TextTiming = {
  /** Start and end time (seconds) of every UTF-16 code unit of the text. */
  start: number[];
  end: number[];
  /** Share of non-space characters found in the alignment (1 = perfect). */
  matchRatio: number;
};

const isSpace = (c: string) => /\s/u.test(c);

/**
 * Lines the alignment up with the script text. Tolerates the small
 * differences a TTS response can have (missing or extra whitespace, a
 * normalised character) and interpolates anything it cannot match.
 */
export function mapAlignmentToText(text: string, alignment: CharacterAlignment): TextTiming {
  const chars = alignment.characters;
  const aStart = alignment.character_start_times_seconds;
  const aEnd = alignment.character_end_times_seconds;
  const start = new Array<number>(text.length).fill(Number.NaN);
  const end = new Array<number>(text.length).fill(Number.NaN);
  let j = 0;
  let matched = 0;
  let nonSpace = 0;

  for (let i = 0; i < text.length; ) {
    const c = String.fromCodePoint(text.codePointAt(i) as number);
    const width = c.length;
    const assign = (k: number) => {
      for (let u = 0; u < width; u++) {
        start[i + u] = aStart[k];
        end[i + u] = aEnd[k];
      }
    };
    if (!isSpace(c)) nonSpace += 1;

    while (j < chars.length && isSpace(chars[j]) && !isSpace(c)) j += 1;
    if (j < chars.length && chars[j] === c) {
      assign(j);
      j += 1;
      if (!isSpace(c)) matched += 1;
    } else if (!isSpace(c)) {
      const ahead = chars.slice(j, j + 8).indexOf(c);
      if (ahead !== -1) {
        j += ahead;
        assign(j);
        j += 1;
        matched += 1;
      }
    }
    i += width;
  }

  fillGaps(start, end);
  return { start, end, matchRatio: nonSpace === 0 ? 1 : matched / nonSpace };
}

/** Interpolates characters without timing between their timed neighbours. */
function fillGaps(start: number[], end: number[]): void {
  const n = start.length;
  let i = 0;
  while (i < n) {
    if (!Number.isNaN(start[i])) {
      i += 1;
      continue;
    }
    let k = i;
    while (k < n && Number.isNaN(start[k])) k += 1;
    const from = i > 0 ? end[i - 1] : k < n ? start[k] : 0;
    const to = k < n ? start[k] : from;
    const count = k - i;
    for (let m = 0; m < count; m++) {
      start[i + m] = from + ((to - from) * m) / count;
      end[i + m] = from + ((to - from) * (m + 1)) / count;
    }
    i = k;
  }
}

export type Interval = { start: number; end: number };

/** Speech regions = the audio minus its silences (short blips are dropped). */
export function speechRegions(silences: Interval[], durationSeconds: number, minRegion = 0.06): Interval[] {
  const regions: Interval[] = [];
  let cursor = 0;
  for (const s of [...silences].sort((a, b) => a.start - b.start)) {
    if (s.start - cursor >= minRegion) regions.push({ start: cursor, end: s.start });
    cursor = Math.max(cursor, s.end);
  }
  if (durationSeconds - cursor >= minRegion) regions.push({ start: cursor, end: durationSeconds });
  return regions;
}

/**
 * Estimates character timing for audio that came without it (for example a
 * recording or the temporary test audio). Phrases (text between spaces) are
 * matched to the speech regions between pauses so the relative lengths fit
 * best, then each phrase's characters are spread over its region by their
 * speaking weight. Accurate to phrase level; word timing is approximate.
 */
export function estimateAlignmentFromSilences(text: string, silences: Interval[], durationSeconds: number): CharacterAlignment {
  const phrases: Array<{ from: number; to: number; weight: number }> = [];
  const re = /\S+/gu;
  for (let m = re.exec(text); m; m = re.exec(text)) {
    phrases.push({ from: m.index, to: m.index + m[0].length, weight: Math.max(0.5, speechWeight(m[0])) });
  }
  let regions = speechRegions(silences, durationSeconds);
  if (phrases.length === 0 || regions.length === 0) throw new Error("No speech found in the audio, or the narration is empty.");

  // More pauses than phrases: the voice paused inside a phrase. Merge the
  // regions separated by the shortest pauses until the counts match.
  while (regions.length > phrases.length) {
    let shortest = 0;
    for (let r = 1; r < regions.length - 1; r++) {
      if (regions[r + 1].start - regions[r].end < regions[shortest + 1].start - regions[shortest].end) shortest = r;
    }
    regions = [
      ...regions.slice(0, shortest),
      { start: regions[shortest].start, end: regions[shortest + 1].end },
      ...regions.slice(shortest + 2),
    ];
  }

  // Partition the phrases into regions.length consecutive groups whose
  // speaking weight best matches each region's length (dynamic programming).
  const P = phrases.length;
  const R = regions.length;
  const totalWeight = phrases.reduce((s, p) => s + p.weight, 0);
  const totalSpeech = regions.reduce((s, r) => s + (r.end - r.start), 0);
  const secondsPerWeight = totalSpeech / totalWeight;
  const prefix = [0];
  for (const p of phrases) prefix.push(prefix[prefix.length - 1] + p.weight);
  const cost = Array.from({ length: R + 1 }, () => new Array<number>(P + 1).fill(Infinity));
  const back = Array.from({ length: R + 1 }, () => new Array<number>(P + 1).fill(-1));
  cost[0][0] = 0;
  for (let r = 1; r <= R; r++) {
    const length = regions[r - 1].end - regions[r - 1].start;
    for (let p = r; p <= P - (R - r); p++) {
      for (let q = r - 1; q < p; q++) {
        if (cost[r - 1][q] === Infinity) continue;
        const expected = (prefix[p] - prefix[q]) * secondsPerWeight;
        const c = cost[r - 1][q] + (length - expected) ** 2 / Math.max(length, 0.2);
        if (c < cost[r][p]) {
          cost[r][p] = c;
          back[r][p] = q;
        }
      }
    }
  }
  const groups: Array<[number, number]> = [];
  for (let r = R, p = P; r > 0; r--) {
    const q = back[r][p];
    groups.unshift([q, p]);
    p = q;
  }

  const starts = new Array<number>(text.length).fill(Number.NaN);
  const ends = new Array<number>(text.length).fill(Number.NaN);
  groups.forEach(([q, p], r) => {
    const region = regions[r];
    const from = phrases[q].from;
    const to = phrases[p - 1].to;
    // Spaces inside one region are short pauses: give them a little weight.
    const weights: number[] = [];
    for (let i = from; i < to; i++) weights.push(/\s/u.test(text[i]) ? 0.3 : speechWeight(text[i]));
    const sum = weights.reduce((s, w) => s + w, 0) || 1;
    let t = region.start;
    for (let i = from; i < to; i++) {
      const d = ((region.end - region.start) * weights[i - from]) / sum;
      starts[i] = t;
      ends[i] = t + d;
      t += d;
    }
  });
  fillGaps(starts, ends);
  return {
    characters: Array.from({ length: text.length }, (_, i) => text[i]),
    character_start_times_seconds: starts,
    character_end_times_seconds: ends,
  };
}
