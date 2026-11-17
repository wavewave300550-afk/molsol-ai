import { Audio } from "@remotion/media";
import { AbsoluteFill, type CalculateMetadataFunction, Sequence, staticFile, Track } from "remotion";
import { z } from "zod";
import { Background } from "./components/Background.tsx";
import { ProgressBar } from "./components/ProgressBar.tsx";
import { TestBadge } from "./components/TestBadge.tsx";
import { getAudioDuration } from "./get-audio-duration.ts";
import { VIDEO } from "./lib/config.ts";
import type { Timeline } from "./lib/timeline.ts";
import { SceneView } from "./scenes/SceneView.tsx";
import { COLORS } from "./theme.ts";

export const episodeSchema = z.looseObject({
  episodeId: z.string().regex(/^[a-z0-9][a-z0-9-]*$/),
});

export type EpisodeProps = z.infer<typeof episodeSchema> & { timeline?: Timeline };

/**
 * The narration decides the length: calculateMetadata loads the episode's
 * timeline (built from the narration by `npm run render`) and re-measures
 * the narration file, refusing to render if they disagree.
 */
export const calculateEpisodeMetadata: CalculateMetadataFunction<EpisodeProps> = async ({ props, abortSignal }) => {
  const url = staticFile(`episodes/${props.episodeId}/timeline.json`);
  const response = await fetch(url, { signal: abortSignal });
  if (!response.ok) {
    throw new Error(`No timeline for "${props.episodeId}". Build it with: npm run render -- ${props.episodeId} (or npm run pipeline:test)`);
  }
  const timeline = (await response.json()) as Timeline;
  if (timeline.fps !== VIDEO.fps || timeline.width !== VIDEO.width || timeline.height !== VIDEO.height) {
    throw new Error("The timeline was built for a different video format. Rebuild it.");
  }
  const audioSeconds = await getAudioDuration(staticFile(timeline.audio.src));
  if (Math.abs(audioSeconds - timeline.audio.durationSeconds) > 0.05) {
    throw new Error(`The narration changed (${audioSeconds.toFixed(2)} s, timeline has ${timeline.audio.durationSeconds.toFixed(2)} s). Rebuild the timeline.`);
  }
  if (timeline.durationInFrames < Math.ceil(audioSeconds * VIDEO.fps)) {
    throw new Error("The timeline is shorter than the narration; narration must never be cut.");
  }
  return {
    durationInFrames: timeline.durationInFrames,
    props: { ...props, timeline },
    defaultOutName: timeline.episodeId,
  };
};

/**
 * Scenes, subtitles and cues are generated from the episode script and its
 * narration timing, so their timing is not edited by hand in Studio: change
 * the script (and narration) instead, and the video follows.
 */
export const Episode: React.FC<EpisodeProps> = ({ timeline }) => {
  if (!timeline) throw new Error("The episode timeline is missing; calculateMetadata loads it.");
  // Anything that is not a real episode (pipeline and voice tests) or uses
  // temporary test audio carries the TEST badge.
  const isTest = timeline.kind !== "episode" || timeline.audio.narrationSource === "test-audio";
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      <Background />
      <Track name="Scenes">
        {timeline.scenes.map((scene) => (
          <Sequence key={scene.id} name={`${scene.index + 1}. ${scene.label}`} from={scene.from} durationInFrames={scene.durationInFrames}>
            <SceneView scene={scene} total={timeline.scenes.length} allSources={timeline.sources} />
          </Sequence>
        ))}
      </Track>
      <ProgressBar scenes={timeline.scenes} />
      {isTest ? <TestBadge /> : null}
      <Audio name="Narration" src={staticFile(timeline.audio.src)} />
    </AbsoluteFill>
  );
};
