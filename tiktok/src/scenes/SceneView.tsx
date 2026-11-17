import { AbsoluteFill } from "remotion";
import { SceneHeader } from "../components/SceneHeader.tsx";
import { ThaiCaptions } from "../components/ThaiCaptions.tsx";
import type { Source } from "../lib/schema.ts";
import type { TimelineScene } from "../lib/timeline.ts";
import { ChartScene } from "./ChartScene.tsx";
import { FactScene } from "./FactScene.tsx";
import { ImageScene } from "./ImageScene.tsx";
import { MoleculeScene } from "./MoleculeScene.tsx";
import { ProcessScene } from "./ProcessScene.tsx";
import { SourcesScene } from "./SourcesScene.tsx";
import { TitleScene } from "./TitleScene.tsx";

const Visual: React.FC<{ scene: TimelineScene; sources: Source[] }> = ({ scene, sources }) => {
  const { visual, cues } = scene;
  switch (visual.type) {
    case "title":
      return <TitleScene visual={visual} />;
    case "molecule":
      return <MoleculeScene visual={visual} cues={cues} />;
    case "chart":
      return <ChartScene visual={visual} cues={cues} />;
    case "process":
      return <ProcessScene visual={visual} cues={cues} />;
    case "fact":
      return <FactScene visual={visual} cues={cues} />;
    case "image":
      return <ImageScene visual={visual} />;
    case "sources":
      return <SourcesScene visual={visual} sources={sources} />;
  }
};

/** One scene: its visual, header with sources, and its own subtitles. */
export const SceneView: React.FC<{ scene: TimelineScene; total: number; allSources: Source[] }> = ({ scene, total, allSources }) => {
  const cited = allSources.filter((s) => scene.sourceIds.includes(s.id));
  return (
    <AbsoluteFill>
      <SceneHeader index={scene.index} total={total} label={scene.label} sources={cited} />
      <Visual scene={scene} sources={allSources} />
      <ThaiCaptions pages={scene.captions} />
    </AbsoluteFill>
  );
};
