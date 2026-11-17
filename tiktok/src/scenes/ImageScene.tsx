import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { progress } from "../components/anim.ts";
import { BODY_FONT } from "../fonts.ts";
import type { Visual } from "../lib/schema.ts";
import { COLORS } from "../theme.ts";
import { VisualArea, VisualTitle } from "./VisualArea.tsx";

type ImageVisual = Extract<Visual, { type: "image" }>;

/** A scientific illustration from public/, slowly zooming, with its credit. */
export const ImageScene: React.FC<{ visual: ImageVisual }> = ({ visual }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <VisualArea>
      {visual.title ? <VisualTitle>{visual.title}</VisualTitle> : null}
      <div
        style={{
          flex: 1,
          marginTop: 20,
          borderRadius: 36,
          overflow: "hidden",
          backgroundColor: "rgba(148, 163, 184, 0.08)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: progress(frame, 4, 14),
        }}
      >
        <Img
          src={staticFile(visual.src)}
          alt={visual.alt}
          style={{
            width: "86%",
            height: "92%",
            objectFit: "contain",
            scale: String(interpolate(frame, [0, durationInFrames], [1, 1.07], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })),
          }}
        />
      </div>
      <div style={{ marginTop: 16, fontFamily: BODY_FONT, fontSize: 30, lineHeight: 1.4, color: COLORS.muted }}>ภาพ: {visual.credit}</div>
    </VisualArea>
  );
};
