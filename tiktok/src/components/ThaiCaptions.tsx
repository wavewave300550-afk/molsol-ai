import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { HEADING_FONT } from "../fonts.ts";
import type { CaptionPage } from "../lib/captions.ts";
import { COLORS, LAYOUT } from "../theme.ts";

/**
 * TikTok-style Thai subtitles. Pages and word times come from the narration
 * timing (timeline.json); the word being spoken is highlighted. Each word is
 * an inline block, so lines only wrap between words.
 */
export const ThaiCaptions: React.FC<{ pages: CaptionPage[] }> = ({ pages }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;
  const page = pages.find((p) => ms >= p.startMs && ms < p.endMs);
  if (!page) return null;
  const sinceStart = frame - Math.round((page.startMs / 1000) * fps);

  return (
    <div
      style={{
        position: "absolute",
        left: LAYOUT.left,
        width: LAYOUT.contentWidth,
        bottom: 1920 - LAYOUT.captionsBottom,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          fontFamily: HEADING_FONT,
          fontWeight: 700,
          fontSize: 62,
          lineHeight: 1.45,
          textAlign: "center",
          textWrap: "balance",
          color: COLORS.text,
          padding: "14px 28px 18px",
          borderRadius: 30,
          backgroundColor: "rgba(2, 6, 23, 0.62)",
          opacity: interpolate(sinceStart, [0, 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          scale: interpolate(sinceStart, [0, 7], [0.94, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        {page.tokens.map((token, i) => {
          const next = page.tokens[i + 1];
          const active = ms >= token.startMs && (next ? ms < next.startMs : true);
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                whiteSpace: "pre",
                color: active ? COLORS.highlight : COLORS.text,
                opacity: ms >= token.startMs ? 1 : 0.72,
                textShadow: "0 4px 16px rgba(0,0,0,0.55)",
              }}
            >
              {token.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};
