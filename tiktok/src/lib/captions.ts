/**
 * Thai subtitles from the narration timing.
 *
 * Tokens are words from Intl.Segmenter, so a subtitle never breaks inside a
 * dictionary word, and glossary terms (science loanwords the dictionary does
 * not know) are kept whole. Pages follow how the line is spoken: a new page
 * starts at a pause, at a phrase break (a space in the script) once the page
 * has some text, or when it would get too long to read. A page that has to be
 * split is cut at the best point: a phrase break if possible, never right
 * after a word that leads into the next (ความ, การ, ที่, ของ ...). Times come
 * straight from the narration's character timing.
 */
import type { Caption } from "@remotion/captions";
import { CAPTIONS } from "./config.ts";
import { NO_BREAK_AFTER } from "./glossary.ts";
import { normalizeNarration, segmentWords, stripTrailingNonWord, visibleLength } from "./text.ts";

export type CaptionPage = {
  /** Milliseconds from the start of the scene. */
  startMs: number;
  endMs: number;
  text: string;
  /** Remotion Caption tokens; a leading space marks a phrase break. */
  tokens: Caption[];
};

export type Token = { text: string; from: number; to: number; spaceBefore: boolean; startMs: number; endMs: number };

export type CaptionInput = {
  text: string;
  /** Scene range in `text` (UTF-16 offsets, end exclusive). */
  rangeStart: number;
  rangeEnd: number;
  /** Character timing for `text`, seconds. */
  start: number[];
  end: number[];
  sceneStartSeconds: number;
  sceneEndSeconds: number;
  /** Terms that must stay in one piece. */
  keepTogether?: readonly string[];
  options?: typeof CAPTIONS;
};

export function tokenize(input: CaptionInput): Token[] {
  const { text, rangeStart, rangeEnd, start, end } = input;
  const tokens: Token[] = [];
  let pendingSpace = false;
  let pendingPrefix = "";
  for (const seg of segmentWords(text.slice(rangeStart, rangeEnd))) {
    const from = rangeStart + seg.index;
    const to = from + seg.text.length;
    if (/^\s+$/u.test(seg.text)) {
      pendingSpace = tokens.length > 0;
      continue;
    }
    if (!seg.isWordLike) {
      // Punctuation sticks to the word before it (or the next one at the start).
      const previous = tokens[tokens.length - 1];
      if (previous && !pendingSpace) {
        previous.text += seg.text;
        previous.to = to;
      } else {
        pendingPrefix += seg.text;
      }
      continue;
    }
    tokens.push({
      text: pendingPrefix + seg.text,
      from: from - pendingPrefix.length,
      to,
      spaceBefore: pendingSpace,
      startMs: start[from] * 1000,
      endMs: end[to - 1] * 1000,
    });
    pendingSpace = false;
    pendingPrefix = "";
  }
  return mergeProtected(tokens, protectedRanges(text, rangeStart, rangeEnd, input.keepTogether ?? []));
}

function protectedRanges(text: string, rangeStart: number, rangeEnd: number, terms: readonly string[]) {
  const scene = text.slice(rangeStart, rangeEnd);
  const ranges: Array<{ from: number; to: number }> = [];
  for (const raw of terms) {
    const term = normalizeNarration(raw);
    if (!term || /\s/u.test(term)) continue;
    for (let at = scene.indexOf(term); at !== -1; at = scene.indexOf(term, at + 1)) {
      ranges.push({ from: rangeStart + at, to: rangeStart + at + term.length });
    }
  }
  return ranges;
}

/** Joins neighbouring tokens that both cover the same protected term. */
function mergeProtected(tokens: Token[], ranges: Array<{ from: number; to: number }>): Token[] {
  if (ranges.length === 0) return tokens;
  const overlaps = (t: Token, r: { from: number; to: number }) => t.from < r.to && r.from < t.to;
  const merged: Token[] = [];
  for (const token of tokens) {
    const previous = merged[merged.length - 1];
    if (previous && !token.spaceBefore && ranges.some((r) => overlaps(previous, r) && overlaps(token, r))) {
      previous.text += token.text;
      previous.to = token.to;
      previous.endMs = token.endMs;
    } else {
      merged.push({ ...token });
    }
  }
  return merged;
}

const pageText = (tokens: Token[]) => tokens.map((t, i) => (i > 0 && t.spaceBefore ? " " : "") + t.text).join("");

/** How many tokens to keep on the current page when it has to be split. */
function chooseSplit(tokens: Token[], maxChars: number): number {
  let best = tokens.length - 1;
  let bestScore = Number.NEGATIVE_INFINITY;
  for (let k = 1; k < tokens.length; k++) {
    const length = visibleLength(pageText(tokens.slice(0, k)));
    if (length > maxChars && k > 1) break;
    let score = length / maxChars;
    if (tokens[k].spaceBefore) score += 3;
    if (NO_BREAK_AFTER.has(stripTrailingNonWord(tokens[k - 1].text))) score -= 4;
    if (score > bestScore) {
      best = k;
      bestScore = score;
    }
  }
  return best;
}

export function buildCaptionPages(input: CaptionInput): CaptionPage[] {
  const o = input.options ?? CAPTIONS;
  const groups: Token[][] = [];
  let current: Token[] = [];
  const flush = (count: number) => {
    groups.push(current.slice(0, count));
    current = current.slice(count);
  };
  for (const token of tokenize(input)) {
    if (current.length > 0) {
      const last = current[current.length - 1];
      const hardBreak =
        token.startMs - last.endMs > o.pauseBreakMs ||
        (token.spaceBefore && visibleLength(pageText(current)) >= o.minCharsAtPhraseBreak) ||
        token.endMs - current[0].startMs > o.maxPageMs;
      if (hardBreak) flush(current.length);
    }
    current.push(token);
    while (current.length > 1 && visibleLength(pageText(current)) > o.maxChars) {
      flush(chooseSplit(current, o.maxChars));
    }
  }
  if (current.length) groups.push(current);

  const offsetMs = input.sceneStartSeconds * 1000;
  const sceneEndMs = input.sceneEndSeconds * 1000;
  return groups.map((group, g) => {
    const next = groups[g + 1];
    const lastEnd = group[group.length - 1].endMs;
    let endMs = lastEnd + o.holdMs;
    if (next && next[0].startMs - endMs < 250) endMs = next[0].startMs;
    endMs = Math.min(endMs, next ? next[0].startMs : sceneEndMs);
    const rel = (ms: number) => Math.max(0, Math.round(ms - offsetMs));
    return {
      startMs: rel(group[0].startMs),
      endMs: rel(endMs),
      text: pageText(group),
      tokens: group.map((t, i) => ({
        text: (i > 0 && t.spaceBefore ? " " : "") + t.text,
        startMs: rel(t.startMs),
        endMs: rel(t.endMs),
        timestampMs: rel((t.startMs + t.endMs) / 2),
        confidence: null,
        ...(i === group.length - 1 ? { pageBreakAfter: true } : {}),
      })),
    };
  });
}
