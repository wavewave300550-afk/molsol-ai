/**
 * Thai text helpers shared by validation, narration, timing and captions.
 *
 * Thai is written without spaces between words; spaces separate phrases and
 * sentences. Word boundaries come from Intl.Segmenter (ICU dictionary), which
 * both Node and Chrome provide.
 */

const INVISIBLE = /[​⁠﻿]/g;
const COMBINING = /\p{Mn}/u;
const LETTER_OR_DIGIT = /[\p{L}\p{N}]/u;

/**
 * The exact text that is sent to the voice and shown as subtitles: NFC,
 * no zero-width characters, single spaces, trimmed.
 */
export function normalizeNarration(text: string): string {
  return text
    .normalize("NFC")
    .replace(INVISIBLE, "")
    .replace(/[\s ]+/g, " ")
    .trim();
}

/** Characters that take horizontal space (Thai vowel and tone marks do not). */
export function visibleLength(text: string): number {
  let length = 0;
  for (const char of text) if (!COMBINING.test(char)) length += 1;
  return length;
}

/** Relative speaking time of a piece of text, for estimates and test audio. */
export function speechWeight(text: string): number {
  let weight = 0;
  for (const char of text) {
    if (COMBINING.test(char)) weight += 0.35;
    else if (LETTER_OR_DIGIT.test(char)) weight += 1;
  }
  return weight;
}

export type WordSegment = { text: string; index: number; isWordLike: boolean };

let segmenter: Intl.Segmenter | null = null;

export function segmentWords(text: string): WordSegment[] {
  segmenter ??= new Intl.Segmenter("th", { granularity: "word" });
  return Array.from(segmenter.segment(text), (s) => ({
    text: s.segment,
    index: s.index,
    isWordLike: Boolean(s.isWordLike),
  }));
}

/** Trailing characters that do not change how a sentence ends (punctuation, ๆ, ฯ). */
const TRAILING_NON_WORD = /[\s\p{P}\p{S}ๆฯ]+$/u;

/**
 * Splits narration into utterances the way it will be read: at spaces and
 * sentence punctuation. Each piece is returned without trailing punctuation.
 */
export function utterances(text: string): string[] {
  return normalizeNarration(text)
    .split(/[\s.!?…,;:]+/u)
    .map((piece) => piece.replace(TRAILING_NON_WORD, ""))
    .filter((piece) => piece.length > 0);
}

export function stripTrailingNonWord(text: string): string {
  return text.replace(TRAILING_NON_WORD, "");
}
