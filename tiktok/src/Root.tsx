import "./fonts.ts";
import { Composition } from "remotion";
import { calculateEpisodeMetadata, Episode, episodeSchema } from "./Episode.tsx";

/**
 * One composition renders every episode. Its length is a placeholder:
 * calculateMetadata replaces it with the length of the episode's narration.
 * Render with: npm run render -- <episode-id>
 */
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Episode"
      component={Episode}
      durationInFrames={2700}
      fps={30}
      width={1080}
      height={1920}
      schema={episodeSchema}
      defaultProps={{ episodeId: "pipeline-test" }}
      calculateMetadata={calculateEpisodeMetadata}
    />
  );
};
