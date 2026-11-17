import { useCurrentFrame } from "remotion";
import { progress } from "../components/anim.ts";
import { BODY_FONT, HEADING_FONT } from "../fonts.ts";
import type { Source, Visual } from "../lib/schema.ts";
import { COLORS } from "../theme.ts";
import { VisualArea, VisualTitle } from "./VisualArea.tsx";

type SourcesVisual = Extract<Visual, { type: "sources" }>;

/** End card listing every source of the episode. */
export const SourcesScene: React.FC<{ visual: SourcesVisual; sources: Source[] }> = ({ visual, sources }) => {
  const frame = useCurrentFrame();
  const compact = sources.length > 3;
  return (
    <VisualArea>
      <VisualTitle>{visual.title}</VisualTitle>
      <div style={{ display: "flex", flexDirection: "column", gap: compact ? 16 : 26, marginTop: 26 }}>
        {sources.map((source, i) => {
          const link = source.doi ? `doi.org/${source.doi}` : source.url?.replace(/^https?:\/\//, "");
          return (
            <div key={source.id} style={{ display: "flex", gap: 22, opacity: progress(frame, 8 + i * 8, 12) }}>
              <div style={{ fontFamily: HEADING_FONT, fontWeight: 800, fontSize: compact ? 34 : 40, color: COLORS.accent, minWidth: 44 }}>{i + 1}</div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontFamily: HEADING_FONT, fontWeight: 700, fontSize: compact ? 32 : 38, color: COLORS.text, lineHeight: 1.3 }}>{source.label}</div>
                <div style={{ fontFamily: BODY_FONT, fontSize: compact ? 23 : 26, color: COLORS.muted, lineHeight: 1.4 }}>{source.citation}</div>
                {link ? (
                  <div style={{ fontFamily: BODY_FONT, fontSize: compact ? 23 : 26, color: COLORS.accent, lineHeight: 1.4, overflowWrap: "anywhere" }}>{link}</div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </VisualArea>
  );
};
