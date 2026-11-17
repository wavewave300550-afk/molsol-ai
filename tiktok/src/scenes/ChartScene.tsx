import { useCurrentFrame } from "remotion";
import { formatNumber, progress } from "../components/anim.ts";
import { BODY_FONT, HEADING_FONT } from "../fonts.ts";
import type { Visual } from "../lib/schema.ts";
import { COLORS, LAYOUT, SERIES } from "../theme.ts";
import { VisualArea, VisualTitle } from "./VisualArea.tsx";

type ChartVisual = Extract<Visual, { type: "chart" }>;

const NAME_HEIGHT = 104;
const VALUE_HEIGHT = 66;
const BAR_MAX = 280;

/**
 * Bar chart whose bars grow when the narration names them. Negative values
 * (such as log S) hang below the zero line; when every value is negative
 * the names sit above the line so bars and values have the space below.
 */
export const ChartScene: React.FC<{ visual: ChartVisual; cues: Record<string, number> }> = ({ visual, cues }) => {
  const frame = useCurrentFrame();
  const values = visual.bars.map((b) => b.value);
  const maxPos = Math.max(0, ...values);
  const maxNeg = Math.max(0, ...values.map((v) => -v));
  const pxPerUnit = BAR_MAX / (maxPos + maxNeg || 1);
  const namesOnTop = maxPos === 0;
  const zeroY = namesOnTop ? NAME_HEIGHT : VALUE_HEIGHT + maxPos * pxPerUnit;
  const plotHeight = namesOnTop
    ? NAME_HEIGHT + maxNeg * pxPerUnit + VALUE_HEIGHT
    : zeroY + maxNeg * pxPerUnit + (maxNeg > 0 ? VALUE_HEIGHT : 0) + NAME_HEIGHT;
  const gap = 40;
  const columnWidth = Math.min(210, (LAYOUT.contentWidth - gap * (visual.bars.length + 1)) / visual.bars.length);
  const decimals = visual.decimals ?? 1;
  const startOf = (cue: string | undefined, i: number) => (cue !== undefined ? (cues[cue] ?? 0) : 14 + i * 10);

  return (
    <VisualArea>
      <VisualTitle>{visual.title}</VisualTitle>
      <div style={{ flexShrink: 0, marginTop: 4, fontFamily: BODY_FONT, fontWeight: 600, fontSize: 36, color: COLORS.muted, opacity: progress(frame, 6, 12) }}>
        {visual.unit}
      </div>
      <div style={{ position: "relative", flexShrink: 0, height: plotHeight, marginTop: 22 }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: zeroY - 2, height: 4, borderRadius: 2, backgroundColor: "rgba(248,250,252,0.6)" }} />
        {visual.bars.map((bar, i) => {
          const start = startOf(bar.cue, i);
          const grown = progress(frame, start, 20);
          const length = Math.abs(bar.value) * pxPerUnit * grown;
          const negative = bar.value < 0;
          const left = gap + i * (columnWidth + gap);
          const color = SERIES[i % SERIES.length];
          return (
            <div key={bar.label}>
              <div
                style={{
                  position: "absolute",
                  left,
                  width: columnWidth,
                  top: negative ? zeroY : zeroY - length,
                  height: length,
                  borderRadius: negative ? "0 0 18px 18px" : "18px 18px 0 0",
                  backgroundColor: color,
                  boxShadow: `0 0 36px ${color}55`,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left,
                  width: columnWidth,
                  top: negative ? zeroY + length + 6 : zeroY - length - VALUE_HEIGHT + 8,
                  textAlign: "center",
                  fontFamily: HEADING_FONT,
                  fontWeight: 800,
                  fontSize: 46,
                  lineHeight: `${VALUE_HEIGHT - 8}px`,
                  color: COLORS.text,
                  opacity: grown,
                }}
              >
                {formatNumber(bar.value * grown, decimals)}
              </div>
              <div
                style={{
                  position: "absolute",
                  left: left - gap / 2,
                  width: columnWidth + gap,
                  top: namesOnTop ? 0 : plotHeight - NAME_HEIGHT,
                  height: NAME_HEIGHT,
                  textAlign: "center",
                  opacity: 0.35 + 0.65 * progress(frame, start, 10),
                }}
              >
                <div style={{ fontFamily: HEADING_FONT, fontWeight: 700, fontSize: 40, lineHeight: 1.3, color }}>{bar.label}</div>
                {bar.sublabel ? <div style={{ fontFamily: BODY_FONT, fontSize: 30, lineHeight: 1.35, color: COLORS.muted }}>{bar.sublabel}</div> : null}
              </div>
            </div>
          );
        })}
      </div>
      {visual.note ? (
        <div style={{ flexShrink: 0, marginTop: 18, fontFamily: BODY_FONT, fontWeight: 600, fontSize: 36, lineHeight: 1.4, color: COLORS.accent4, opacity: progress(frame, 30, 14) }}>
          {visual.note}
        </div>
      ) : null}
    </VisualArea>
  );
};
