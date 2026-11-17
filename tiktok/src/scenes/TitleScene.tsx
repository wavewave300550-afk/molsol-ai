import { useCurrentFrame } from "remotion";
import { progress } from "../components/anim.ts";
import { BODY_FONT, HEADING_FONT } from "../fonts.ts";
import type { Visual } from "../lib/schema.ts";
import { COLORS } from "../theme.ts";
import { VisualArea } from "./VisualArea.tsx";

type TitleVisual = Extract<Visual, { type: "title" }>;

export const TitleScene: React.FC<{ visual: TitleVisual }> = ({ visual }) => {
  const frame = useCurrentFrame();
  return (
    <VisualArea style={{ justifyContent: "center" }}>
      <AtomMark />
      {visual.kicker ? (
        <div
          style={{
            alignSelf: "flex-start",
            marginTop: 36,
            padding: "8px 22px",
            borderRadius: 999,
            backgroundColor: COLORS.accent2,
            color: COLORS.background,
            fontFamily: HEADING_FONT,
            fontWeight: 700,
            fontSize: 32,
            letterSpacing: 4,
            opacity: progress(frame, 0, 10),
          }}
        >
          {visual.kicker}
        </div>
      ) : null}
      <div
        style={{
          marginTop: 30,
          fontFamily: HEADING_FONT,
          fontWeight: 800,
          fontSize: 100,
          lineHeight: 1.28,
          paddingTop: 10,
          color: COLORS.text,
          textWrap: "balance",
          opacity: progress(frame, 4, 14),
          translate: `0px ${(1 - progress(frame, 4, 20)) * 44}px`,
        }}
      >
        {visual.title}
      </div>
      <div style={{ marginTop: 26, width: 180, height: 10, borderRadius: 5, backgroundColor: COLORS.accent, scale: `${progress(frame, 10, 16)} 1`, transformOrigin: "left" }} />
      {visual.subtitle ? (
        <div style={{ marginTop: 30, fontFamily: BODY_FONT, fontWeight: 600, fontSize: 48, lineHeight: 1.45, color: COLORS.muted, opacity: progress(frame, 14, 14) }}>
          {visual.subtitle}
        </div>
      ) : null}
    </VisualArea>
  );
};

/** A small animated atom: nucleus and three orbiting electrons. */
const AtomMark: React.FC = () => {
  const frame = useCurrentFrame();
  const size = 230;
  const c = size / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ opacity: progress(frame, 0, 16), scale: String(0.7 + 0.3 * progress(frame, 0, 20)) }}>
      {[0, 60, 120].map((angle, i) => {
        const t = ((frame * (1.6 + i * 0.35)) / 60) * Math.PI;
        const ex = c + 100 * Math.cos(t);
        const ey = c + 36 * Math.sin(t);
        const rad = (angle * Math.PI) / 180;
        const x = c + (ex - c) * Math.cos(rad) - (ey - c) * Math.sin(rad);
        const y = c + (ex - c) * Math.sin(rad) + (ey - c) * Math.cos(rad);
        return (
          <g key={angle}>
            <ellipse cx={c} cy={c} rx={100} ry={36} fill="none" stroke={COLORS.accent} strokeOpacity={0.55} strokeWidth={4} transform={`rotate(${angle} ${c} ${c})`} />
            <circle cx={x} cy={y} r={9} fill={COLORS.accent2} />
          </g>
        );
      })}
      <circle cx={c} cy={c} r={20} fill={COLORS.accent3} />
    </svg>
  );
};
