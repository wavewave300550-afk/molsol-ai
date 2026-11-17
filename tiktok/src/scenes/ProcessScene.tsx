import { useCurrentFrame } from "remotion";
import { progress } from "../components/anim.ts";
import { BODY_FONT, HEADING_FONT } from "../fonts.ts";
import type { Visual } from "../lib/schema.ts";
import { COLORS } from "../theme.ts";
import { VisualArea, VisualTitle } from "./VisualArea.tsx";

type ProcessVisual = Extract<Visual, { type: "process" }>;

/** Steps light up one by one as the narration reaches them. */
export const ProcessScene: React.FC<{ visual: ProcessVisual; cues: Record<string, number> }> = ({ visual, cues }) => {
  const frame = useCurrentFrame();
  const starts = visual.steps.map((step, i) => (step.cue !== undefined ? (cues[step.cue] ?? 0) : 16 + i * 24));
  const cardHeight = visual.steps.length > 4 ? 104 : 128;

  return (
    <VisualArea>
      <VisualTitle>{visual.title}</VisualTitle>
      <div style={{ display: "flex", flexDirection: "column", gap: 22, marginTop: 30 }}>
        {visual.steps.map((step, i) => {
          const shown = progress(frame, starts[i] - 4, 12);
          const active = frame >= starts[i] && (i === starts.length - 1 || frame < starts[i + 1]);
          const done = i < starts.length - 1 && frame >= starts[i + 1];
          return (
            <div
              key={step.label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 26,
                height: cardHeight,
                padding: "0 28px",
                borderRadius: 28,
                backgroundColor: active ? "rgba(56, 189, 248, 0.16)" : "rgba(148, 163, 184, 0.08)",
                border: `3px solid ${active ? COLORS.accent : "rgba(148, 163, 184, 0.22)"}`,
                opacity: 0.25 + 0.75 * shown,
                translate: `${(1 - shown) * 40}px 0px`,
                scale: active ? "1.02" : "1",
              }}
            >
              <div
                style={{
                  width: 74,
                  height: 74,
                  flexShrink: 0,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  backgroundColor: done ? COLORS.accent2 : active ? COLORS.accent : "rgba(148, 163, 184, 0.25)",
                  color: COLORS.background,
                  fontFamily: HEADING_FONT,
                  fontWeight: 800,
                  fontSize: 38,
                }}
              >
                {done ? "✓" : i + 1}
              </div>
              <div>
                <div style={{ fontFamily: HEADING_FONT, fontWeight: 700, fontSize: 46, lineHeight: 1.3, color: COLORS.text }}>{step.label}</div>
                {step.detail ? <div style={{ fontFamily: BODY_FONT, fontSize: 30, color: COLORS.muted, lineHeight: 1.35 }}>{step.detail}</div> : null}
              </div>
            </div>
          );
        })}
      </div>
    </VisualArea>
  );
};
