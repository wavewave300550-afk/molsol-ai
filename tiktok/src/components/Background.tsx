import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { COLORS } from "../theme.ts";

const PARTICLES = Array.from({ length: 26 }, (_, i) => ({
  x: random(`x-${i}`) * 1080,
  y: random(`y-${i}`) * 1920,
  size: 4 + random(`s-${i}`) * 8,
  speed: 0.25 + random(`v-${i}`) * 0.6,
  color: i % 3 === 0 ? COLORS.accent2 : COLORS.accent,
  opacity: 0.12 + random(`o-${i}`) * 0.22,
}));

/** Deep-blue lab backdrop with a faint grid and slowly rising particles. */
export const Background: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 70% at 50% 18%, ${COLORS.backgroundGlow} 0%, ${COLORS.background} 62%)`,
      }}
    >
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(148,163,184,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.07) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
        }}
      />
      <Particles />
    </AbsoluteFill>
  );
};

const Particles: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <>
      {PARTICLES.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: p.x,
            top: (((p.y - frame * p.speed) % 1920) + 1920) % 1920,
            width: p.size,
            height: p.size,
            borderRadius: "50%",
            backgroundColor: p.color,
            opacity: p.opacity,
          }}
        />
      ))}
    </>
  );
};
