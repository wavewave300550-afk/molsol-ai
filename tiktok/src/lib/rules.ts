/**
 * Script checks run before approval, before narration and before rendering.
 * Errors block the pipeline; warnings are for the human reviewer.
 */
import { TTS } from "./config.ts";
import { checkVideoDuration, estimateVideoSeconds, formatSeconds } from "./duration.ts";
import type { Issue } from "./issues.ts";
import { PROFANITY, PROFANITY_HINTS } from "./profanity.ts";
import type { Episode, Scene, Visual } from "./schema.ts";
import { normalizeNarration, segmentWords, stripTrailingNonWord } from "./text.ts";

/** Polite particles that must not end a sentence in the narration. */
export const FORBIDDEN_ENDINGS = ["ครับ", "ค่ะ", "คะ"] as const;

export type ForbiddenEnding = { particle: string; context: string };

/**
 * Finds polite particles that end an utterance. A word counts when it IS the
 * particle (the segmenter isolates it even with no space after it, as in
 * "...ได้ครับวันนี้...") or when it ends with the particle and is followed by
 * a space, punctuation or the end of the text ("ขอบคุณนะคะ", "ครับๆ").
 */
export function findForbiddenEndings(narration: string): ForbiddenEnding[] {
  const text = normalizeNarration(narration);
  const segments = segmentWords(text);
  const found: ForbiddenEnding[] = [];
  segments.forEach((seg, i) => {
    if (!seg.isWordLike) return;
    const word = stripTrailingNonWord(seg.text);
    const next = segments[i + 1];
    const atBoundary = !next || !next.isWordLike || /[ๆฯ]$/.test(seg.text);
    const particle = FORBIDDEN_ENDINGS.find((p) => word === p || (atBoundary && word.endsWith(p)));
    if (particle) {
      found.push({ particle, context: text.slice(Math.max(0, seg.index - 18), seg.index + seg.text.length) });
    }
  });
  return found;
}

export function findProfanity(raw: string): { blocked: string[]; review: string[] } {
  let text = normalizeNarration(raw).toLowerCase();
  for (const ok of PROFANITY.allowed) text = text.split(ok).join(" ");
  const words = new Set(
    segmentWords(text)
      .filter((s) => s.isWordLike)
      .map((s) => stripTrailingNonWord(s.text)),
  );
  const english = (term: string) => new RegExp(`(^|[^a-z])${term}([^a-z]|$)`, "i").test(text);
  const blocked = new Set<string>();
  const review = new Set<string>();
  for (const term of PROFANITY.blocked.th) if (words.has(term)) blocked.add(term);
  for (const term of PROFANITY.blocked.thPhrases) if (text.includes(term)) blocked.add(term);
  for (const term of PROFANITY.blocked.en) if (english(term)) blocked.add(term);
  for (const term of PROFANITY.review.th) if (words.has(term)) review.add(term);
  for (const term of PROFANITY.review.en) if (english(term)) review.add(term);
  return { blocked: [...blocked], review: [...review] };
}

/** Every piece of on-screen text in a visual, for the profanity check. */
function visualTexts(visual: Visual): string[] {
  switch (visual.type) {
    case "title":
      return [visual.title, visual.subtitle ?? "", visual.kicker ?? ""];
    case "molecule":
      return [visual.title, visual.caption ?? "", ...visual.atoms.map((a) => a.label ?? "")];
    case "chart":
      return [visual.title, visual.unit, visual.note ?? "", ...visual.bars.flatMap((b) => [b.label, b.sublabel ?? ""])];
    case "process":
      return [visual.title, ...visual.steps.flatMap((s) => [s.label, s.detail ?? ""])];
    case "fact":
      return [visual.title, ...visual.items.flatMap((i) => [i.label, i.prefix ?? "", i.suffix ?? ""])];
    case "image":
      return [visual.title ?? "", visual.alt, visual.credit];
    case "sources":
      return [visual.title];
  }
}

/** Cue ids a visual refers to (bars, steps and items that appear on a spoken word). */
export function visualCueRefs(visual: Visual): string[] {
  switch (visual.type) {
    case "molecule":
      return Object.keys(visual.reveal ?? {});
    case "chart":
      return visual.bars.flatMap((b) => (b.cue ? [b.cue] : []));
    case "process":
      return visual.steps.flatMap((s) => (s.cue ? [s.cue] : []));
    case "fact":
      return visual.items.flatMap((i) => (i.cue ? [i.cue] : []));
    default:
      return [];
  }
}

/** Index of the nth occurrence of `needle` in `haystack`, or -1. */
export function nthIndexOf(haystack: string, needle: string, occurrence = 1): number {
  let index = -1;
  for (let n = 0; n < occurrence; n++) {
    index = haystack.indexOf(needle, index + 1);
    if (index === -1) return -1;
  }
  return index;
}

/** The full text sent to the voice: scene narrations joined by one space. */
export function fullNarration(scenes: Array<Pick<Scene, "narration">>): string {
  return scenes.map((s) => normalizeNarration(s.narration)).join(" ");
}

export type ValidateOptions = {
  /** Checks that a file exists under public/ (images). Node-only, optional. */
  publicFileExists?: (path: string) => boolean;
};

export function validateEpisode(episode: Episode, options: ValidateOptions = {}): Issue[] {
  const issues: Issue[] = [];
  const error = (code: string, message: string, where?: string) => issues.push({ level: "error", code, message, where });
  const warn = (code: string, message: string, where?: string) => issues.push({ level: "warning", code, message, where });
  const sourceIds = new Set(episode.sources.map((s) => s.id));
  const usedSources = new Set<string>();

  const duplicates = (ids: string[]) => ids.filter((id, i) => ids.indexOf(id) !== i);
  for (const id of duplicates(episode.scenes.map((s) => s.id))) error("DUPLICATE_SCENE_ID", `Scene id "${id}" is used twice.`);
  for (const id of duplicates(episode.sources.map((s) => s.id))) error("DUPLICATE_SOURCE_ID", `Source id "${id}" is used twice.`);

  for (const scene of episode.scenes) {
    const where = scene.id;
    const narration = normalizeNarration(scene.narration);

    for (const hit of findForbiddenEndings(narration)) {
      error(
        "POLITE_ENDING",
        `Narration ends a sentence with "${hit.particle}": "…${hit.context}". Remove the particle (no sentence-final ครับ, ค่ะ or คะ).`,
        where,
      );
    }
    const spoken = findProfanity(narration);
    for (const term of spoken.blocked) {
      error("PROFANITY", `Narration contains "${term}".${PROFANITY_HINTS[term] ? ` Hint: ${PROFANITY_HINTS[term]}.` : ""}`, where);
    }
    for (const term of spoken.review) warn("PROFANITY_REVIEW", `Narration contains "${term}"; confirm it is used in its non-offensive sense.`, where);

    const shown = findProfanity([scene.label, ...visualTexts(scene.visual)].join(" "));
    for (const term of shown.blocked) error("PROFANITY_ON_SCREEN", `On-screen text contains "${term}".`, where);
    for (const term of shown.review) warn("PROFANITY_REVIEW", `On-screen text contains "${term}"; confirm it is fine.`, where);

    const cueIds = scene.cues.map((c) => c.id);
    for (const id of duplicates(cueIds)) error("DUPLICATE_CUE_ID", `Cue id "${id}" is used twice.`, where);
    for (const cue of scene.cues) {
      if (nthIndexOf(narration, normalizeNarration(cue.text), cue.occurrence ?? 1) === -1) {
        error("CUE_NOT_IN_NARRATION", `Cue "${cue.id}" waits for "${cue.text}", which is not in this scene's narration.`, where);
      }
    }
    const refs = visualCueRefs(scene.visual);
    for (const ref of refs) if (!cueIds.includes(ref)) error("UNKNOWN_CUE", `The visual refers to cue "${ref}", which is not defined in cues.`, where);
    for (const id of cueIds) if (!refs.includes(id)) warn("UNUSED_CUE", `Cue "${id}" is not used by the visual.`, where);

    const visual = scene.visual;
    if (visual.type === "molecule") {
      const atomIds = visual.atoms.map((a) => a.id);
      for (const id of duplicates(atomIds)) error("DUPLICATE_ATOM_ID", `Atom id "${id}" is used twice.`, where);
      for (const bond of visual.bonds) {
        if (!atomIds.includes(bond.from) || !atomIds.includes(bond.to)) {
          error("UNKNOWN_ATOM", `Bond ${bond.from}-${bond.to} refers to an atom that does not exist.`, where);
        }
      }
      for (const [cue, atoms] of Object.entries(visual.reveal ?? {})) {
        for (const id of atoms) if (!atomIds.includes(id)) error("UNKNOWN_ATOM", `Cue "${cue}" reveals unknown atom "${id}".`, where);
      }
    }
    if (visual.type === "image" && options.publicFileExists && !options.publicFileExists(visual.src)) {
      error("IMAGE_MISSING", `Image public/${visual.src} does not exist.`, where);
    }

    for (const id of scene.sourceIds) {
      if (!sourceIds.has(id)) error("UNKNOWN_SOURCE", `Source "${id}" is not in the sources list.`, where);
      usedSources.add(id);
    }
    const needsSource = scene.factual && visual.type !== "title" && visual.type !== "sources";
    if (needsSource && scene.sourceIds.length === 0) {
      error(
        "FACT_WITHOUT_SOURCE",
        'This scene makes a scientific claim but cites no source. Add sourceIds, or set "factual": false if it makes no claim.',
        where,
      );
    }
  }

  for (const source of episode.sources) {
    if (!source.url && !source.doi) error("SOURCE_WITHOUT_LINK", "Source needs a url or a doi.", source.id);
    if (!source.accessed) {
      warn(
        "SOURCE_NOT_CHECKED",
        'Nobody has confirmed this source yet. Open it, check the claim, then add "accessed": "YYYY-MM-DD".',
        source.id,
      );
    }
    if (!usedSources.has(source.id)) warn("UNUSED_SOURCE", "Source is not cited by any scene.", source.id);
  }

  const last = episode.scenes[episode.scenes.length - 1];
  if (episode.sources.length > 0 && last.visual.type !== "sources") {
    const message = 'The last scene must be a "sources" card listing the references.';
    if (episode.kind === "episode") error("SOURCES_CARD_MISSING", message);
    else warn("SOURCES_CARD_MISSING", message);
  }
  if (episode.scenes[0].visual.type !== "title") warn("NO_TITLE_SCENE", 'The first scene is usually a "title" scene.');

  if (episode.durationTier === "complex" && !episode.complexJustification?.trim()) {
    error("COMPLEX_WITHOUT_REASON", 'durationTier "complex" needs a complexJustification explaining why 90 s is not enough.');
  }

  const characters = fullNarration(episode.scenes).length;
  if (characters > TTS.maxCharactersPerRequest) {
    error(
      "NARRATION_TOO_LONG_FOR_TTS",
      `Narration has ${characters} characters; the limit for one narration request is ${TTS.maxCharactersPerRequest}.`,
    );
  }

  const estimate = estimateVideoSeconds(episode.scenes);
  for (const issue of checkVideoDuration(estimate, episode)) {
    if (issue.level === "error") {
      warn(
        `ESTIMATE_${issue.code}`,
        `Estimated length ${formatSeconds(estimate)} may not fit the "${episode.durationTier}" tier. ` +
          "This is only an estimate; the real narration decides.",
      );
    }
  }
  return issues;
}
