/**
 * Builds the frame-accurate timeline of an episode from its narration.
 *
 * The narration audio is the clock: the video lasts as long as the audio
 * (plus a short tail), each scene starts just before its first spoken word,
 * cues fire on the word they wait for, and subtitles follow the voice.
 * Nothing here can shorten, speed up or trim the narration.
 */
import { type AlignmentFile, mapAlignmentToText } from "./alignment.ts";
import { buildCaptionPages, type CaptionPage } from "./captions.ts";
import { TIMELINE, VIDEO } from "./config.ts";
import { SCIENCE_GLOSSARY } from "./glossary.ts";
import { fullNarration, nthIndexOf, sceneRanges } from "./rules.ts";
import type { Episode, EpisodeKind, Scene, Source, Visual } from "./schema.ts";
import { normalizeNarration } from "./text.ts";

export type TimelineScene = {
  id: string;
  index: number;
  label: string;
  /** First frame of the scene in the video. */
  from: number;
  durationInFrames: number;
  /** When the scene's first and last words are spoken (seconds from video start). */
  speechStartSeconds: number;
  speechEndSeconds: number;
  visual: Visual;
  sourceIds: string[];
  /** Cue id -> frame, relative to the scene's first frame. */
  cues: Record<string, number>;
  captions: CaptionPage[];
};

export type Timeline = {
  version: 1;
  episodeId: string;
  title: string;
  kind: EpisodeKind;
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  durationSeconds: number;
  tailSeconds: number;
  audio: {
    /** Path under public/, for staticFile(). */
    src: string;
    durationSeconds: number;
    timingSource: AlignmentFile["source"];
    /** "test-audio" renders always carry the TEST badge. */
    narrationSource: "elevenlabs" | "local-file" | "test-audio";
  };
  narrationHash: string;
  scenes: TimelineScene[];
  sources: Source[];
  generatedAt: string;
};

export type BuildTimelineInput = {
  episode: Episode;
  alignment: AlignmentFile;
  /** Measured length of the audio file that will play in the video. */
  audioDurationSeconds: number;
  audioSrc: string;
  narrationHash: string;
  narrationSource?: Timeline["audio"]["narrationSource"];
  fps?: number;
  tailSeconds?: number;
};

/** Terms whose subtitle tokens must stay whole in this scene. */
function keepTogether(episode: Episode, scene: Scene): string[] {
  const labels = scene.visual.type === "chart" ? scene.visual.bars.map((b) => b.label) : [];
  return [...SCIENCE_GLOSSARY, ...(episode.glossary ?? []), ...scene.cues.map((c) => c.text), ...labels];
}

export function buildTimeline(input: BuildTimelineInput): Timeline {
  const { episode, alignment, audioDurationSeconds } = input;
  const fps = input.fps ?? VIDEO.fps;
  const tailSeconds = input.tailSeconds ?? TIMELINE.tailSeconds;
  const text = fullNarration(episode.scenes);
  if (normalizeNarration(alignment.text) !== text) {
    throw new Error("The narration audio was made for a different script. Generate the narration again.");
  }
  const timing = mapAlignmentToText(text, alignment.alignment);
  if (timing.matchRatio < 0.9) {
    throw new Error(`Only ${(timing.matchRatio * 100).toFixed(0)}% of the script matches the narration timing.`);
  }

  const ranges = sceneRanges(episode.scenes);
  const speech = ranges.map(({ from, to }) => ({ start: timing.start[from], end: timing.end[to - 1] }));
  const lastSpoken = speech[speech.length - 1].end;
  if (lastSpoken > audioDurationSeconds + 0.05) {
    throw new Error(`Narration timing runs to ${lastSpoken.toFixed(2)} s but the audio is only ${audioDurationSeconds.toFixed(2)} s long.`);
  }

  // The whole audio plays, then the tail: never shorter than the narration.
  const durationInFrames = Math.ceil((audioDurationSeconds + tailSeconds) * fps);

  // A scene cuts in shortly before its first word, but never before the
  // previous scene has finished speaking and never after its own first word.
  const boundaries = speech.map((s, i) =>
    i === 0 ? 0 : Math.min(s.start, Math.max(speech[i - 1].end, s.start - TIMELINE.sceneLeadSeconds)),
  );
  const froms = boundaries.map((b, i) => (i === 0 ? 0 : Math.round(b * fps)));

  const scenes: TimelineScene[] = episode.scenes.map((scene, i) => {
    const from = froms[i];
    const to = i + 1 < froms.length ? froms[i + 1] : durationInFrames;
    const durationInFrames_ = to - from;
    if (durationInFrames_ < TIMELINE.minSceneSeconds * fps) {
      throw new Error(
        `Scene "${scene.id}" would last ${(durationInFrames_ / fps).toFixed(2)} s; scenes need at least ` +
          `${TIMELINE.minSceneSeconds} s of narration. Merge it or give it more narration.`,
      );
    }
    const narration = normalizeNarration(scene.narration);
    const cues: Record<string, number> = {};
    for (const cue of scene.cues) {
      const at = nthIndexOf(narration, normalizeNarration(cue.text), cue.occurrence ?? 1);
      if (at === -1) throw new Error(`Cue "${cue.id}" text is not in scene "${scene.id}".`);
      cues[cue.id] = Math.max(0, Math.round(timing.start[ranges[i].from + at] * fps) - from);
    }
    return {
      id: scene.id,
      index: i,
      label: scene.label,
      from,
      durationInFrames: durationInFrames_,
      speechStartSeconds: speech[i].start,
      speechEndSeconds: speech[i].end,
      visual: scene.visual,
      sourceIds: scene.sourceIds,
      cues,
      captions: buildCaptionPages({
        text,
        rangeStart: ranges[i].from,
        rangeEnd: ranges[i].to,
        start: timing.start,
        end: timing.end,
        sceneStartSeconds: from / fps,
        sceneEndSeconds: to / fps,
        keepTogether: keepTogether(episode, scene),
      }),
    };
  });

  return {
    version: 1,
    episodeId: episode.id,
    title: episode.title,
    kind: episode.kind,
    fps,
    width: VIDEO.width,
    height: VIDEO.height,
    durationInFrames,
    durationSeconds: durationInFrames / fps,
    tailSeconds,
    audio: {
      src: input.audioSrc,
      durationSeconds: audioDurationSeconds,
      timingSource: alignment.source,
      narrationSource: input.narrationSource ?? "test-audio",
    },
    narrationHash: input.narrationHash,
    scenes,
    sources: episode.sources,
    generatedAt: new Date().toISOString(),
  };
}
