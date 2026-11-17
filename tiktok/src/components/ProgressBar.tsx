import { useCurrentFrame } from "remotion";
import type { TimelineScene } from "../lib/timeline.ts";
import { COLORS, LAYOUT } from "../theme.ts";

/** One segment per scene, filling as the narration moves through it. */
export const ProgressBar: React.FC<{ scenes: TimelineScene[] }> = ({ scenes }) => {
  const frame = useCurrentFrame();
  const total = scenes.reduce((sum, s) => sum + s.durationInFrames, 0);
  return (
    <div style={{ position: "absolute", left: LAYOUT.left, top: LAYOUT.progressTop, width: LAYOUT.contentWidth, height: 8, display: "flex", gap: 8 }}>
      {scenes.map((scene) => {
        const filled = Math.min(1, Math.max(0, (frame - scene.from) / scene.durationInFrames));
        return (
          <div
            key={scene.id}
            style={{ flex: scene.durationInFrames / total, height: 8, borderRadius: 4, backgroundColor: "rgba(248,250,252,0.18)", overflow: "hidden" }}
          >
            <div style={{ width: `${filled * 100}%`, height: "100%", backgroundColor: COLORS.accent }} />
          </div>
        );
      })}
    </div>
  );
};
