import { useCurrentFrame } from "remotion";
import { formatNumber, pop, progress } from "../components/anim.ts";
import { HEADING_FONT } from "../fonts.ts";
import type { Visual } from "../lib/schema.ts";
import { COLORS, SERIES } from "../theme.ts";
import { VisualArea, VisualTitle } from "./VisualArea.tsx";

type FactVisual = Extract<Visual, { type: "fact" }>;

/** Big numbers that count up when the narration says them. */
export const FactScene: React.FC<{ visual: FactVisual; cues: Record<string, number> }> = ({ visual, cues }) => {
  const frame = useCurrentFrame();
  const big = visual.items.length <= 2;
  return (
    <VisualArea>
      <VisualTitle>{visual.title}</VisualTitle>
      <div style={{ display: "flex", flexDirection: "column", gap: 24, marginTop: 34 }}>
        {visual.items.map((item, i) => {
          const start = item.cue !== undefined ? (cues[item.cue] ?? 0) : 14 + i * 16;
          const shown = pop(frame, start, 16);
          const counted = progress(frame, start, 26);
          const color = SERIES[i % SERIES.length];
          return (
            <div
              key={item.label}
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 28,
                padding: "16px 34px 20px",
                borderRadius: 30,
                backgroundColor: "rgba(148, 163, 184, 0.08)",
                borderLeft: `10px solid ${color}`,
                opacity: Math.min(1, shown * 1.3),
                scale: String(0.85 + 0.15 * shown),
                transformOrigin: "left center",
              }}
            >
              <div style={{ fontFamily: HEADING_FONT, fontWeight: 800, fontSize: big ? 150 : 120, lineHeight: 1.1, color, minWidth: big ? 0 : 330 }}>
                {item.prefix ?? ""}
                {formatNumber(item.value * counted, item.decimals ?? 0)}
                {item.suffix ?? ""}
              </div>
              <div style={{ fontFamily: HEADING_FONT, fontWeight: 500, fontSize: 40, lineHeight: 1.3, color: COLORS.text }}>{item.label}</div>
            </div>
          );
        })}
      </div>
    </VisualArea>
  );
};
