import { useCurrentFrame } from "remotion";
import { BODY_FONT, HEADING_FONT } from "../fonts.ts";
import type { Source } from "../lib/schema.ts";
import { COLORS, LAYOUT } from "../theme.ts";
import { progress } from "./anim.ts";

const pad = (n: number) => String(n).padStart(2, "0");

/** Scene number and label, plus the sources behind what this scene says. */
export const SceneHeader: React.FC<{ index: number; total: number; label: string; sources: Source[] }> = ({
  index,
  total,
  label,
  sources,
}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ position: "absolute", left: LAYOUT.left, top: LAYOUT.headerTop, width: LAYOUT.contentWidth, opacity: progress(frame, 0, 10) }}>
      <div style={{ fontFamily: HEADING_FONT, fontWeight: 500, fontSize: 36, color: COLORS.muted, letterSpacing: 1 }}>
        <span style={{ color: COLORS.accent, fontWeight: 700 }}>{pad(index + 1)}</span>
        <span> / {pad(total)} · </span>
        <span style={{ color: COLORS.text }}>{label}</span>
      </div>
      {sources.length > 0 ? (
        <div style={{ marginTop: 10, fontFamily: BODY_FONT, fontWeight: 400, fontSize: 30, color: COLORS.muted, lineHeight: 1.35 }}>
          ที่มา: {sources.map((s) => s.label).join(" · ")}
        </div>
      ) : null}
    </div>
  );
};
