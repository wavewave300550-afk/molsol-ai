import { DURATION_TIERS, ESTIMATE, TIMELINE } from "./config.ts";
import type { Issue } from "./issues.ts";
import type { Episode, Scene } from "./schema.ts";
import { normalizeNarration, speechWeight } from "./text.ts";

export const formatSeconds = (seconds: number): string => `${seconds.toFixed(2)} s`;

/**
 * Checks a final video length against the episode's duration tier.
 * The fix for a failure is always to change the script (or, for 90-120 s,
 * to approve the complex tier): narration is never sped up or cut to fit.
 */
export function checkVideoDuration(
  videoSeconds: number,
  episode: Pick<Episode, "durationTier" | "complexJustification">,
): Issue[] {
  const tier = DURATION_TIERS[episode.durationTier];
  const max = DURATION_TIERS.complex.maxSeconds;
  const length = formatSeconds(videoSeconds);
  if (videoSeconds > max) {
    return [
      {
        level: "error",
        code: "DURATION_OVER_MAX",
        message: `Video would be ${length}, over the ${max} s maximum. Shorten the narration; it is never sped up or cut.`,
      },
    ];
  }
  if (videoSeconds > tier.maxSeconds) {
    return [
      {
        level: "error",
        code: "DURATION_OVER_STANDARD",
        message:
          `Video would be ${length}, over the ${tier.maxSeconds} s standard limit. Shorten the narration, ` +
          `or set durationTier "complex" with a complexJustification and approve it again (max ${max} s).`,
      },
    ];
  }
  if (videoSeconds < tier.minSeconds) {
    return [
      {
        level: "error",
        code: "DURATION_UNDER_MIN",
        message: `Video would be ${length}, under the ${tier.minSeconds} s minimum. Add narration.`,
      },
    ];
  }
  if (episode.durationTier === "complex" && videoSeconds <= DURATION_TIERS.standard.maxSeconds) {
    return [
      {
        level: "warning",
        code: "COMPLEX_NOT_NEEDED",
        message: `Video is ${length}, which fits the standard tier; "complex" is not needed.`,
      },
    ];
  }
  return [];
}

/** Rough length of the finished video before any narration exists. */
export function estimateVideoSeconds(scenes: Array<Pick<Scene, "narration">>): number {
  let seconds = 0;
  scenes.forEach((scene, index) => {
    const narration = normalizeNarration(scene.narration);
    seconds += speechWeight(narration) / ESTIMATE.weightedCharsPerSecond;
    seconds += (narration.match(/ /g)?.length ?? 0) * ESTIMATE.phrasePauseSeconds;
    if (index > 0) seconds += ESTIMATE.scenePauseSeconds;
  });
  return seconds + TIMELINE.tailSeconds;
}
