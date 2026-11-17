import { useCurrentFrame } from "remotion";
import { progress } from "../components/anim.ts";
import { HEADING_FONT } from "../fonts.ts";
import { COLORS, LAYOUT } from "../theme.ts";

/** The part of the frame scenes draw in: below the header, above the subtitles. */
export const VisualArea: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div
    style={{
      position: "absolute",
      left: LAYOUT.left,
      top: LAYOUT.visualTop,
      width: LAYOUT.contentWidth,
      height: LAYOUT.visualBottom - LAYOUT.visualTop,
      display: "flex",
      flexDirection: "column",
      ...style,
    }}
  >
    {children}
  </div>
);

export const VisualTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        flexShrink: 0,
        fontFamily: HEADING_FONT,
        fontWeight: 800,
        fontSize: 76,
        lineHeight: 1.3,
        paddingTop: 8,
        color: COLORS.text,
        textWrap: "balance",
        opacity: progress(frame, 2, 12),
        translate: `0px ${(1 - progress(frame, 2, 16)) * 28}px`,
      }}
    >
      {children}
    </div>
  );
};
