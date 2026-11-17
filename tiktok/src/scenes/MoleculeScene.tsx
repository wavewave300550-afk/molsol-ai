import { useCurrentFrame } from "remotion";
import { pop, progress } from "../components/anim.ts";
import { Formula } from "../components/Formula.tsx";
import { BODY_FONT, HEADING_FONT } from "../fonts.ts";
import type { Visual } from "../lib/schema.ts";
import { COLORS, ELEMENT_COLORS, LIGHT_ELEMENTS, LAYOUT } from "../theme.ts";
import { VisualArea, VisualTitle } from "./VisualArea.tsx";

type MoleculeVisual = Extract<Visual, { type: "molecule" }>;

const W = LAYOUT.contentWidth;
const H = 520;
const radiusOf = (element: string) => (element === "H" ? 54 : 74);

/**
 * Atoms appear when the narration names them (the visual's "reveal" cues);
 * a bond draws itself once both of its atoms are on screen.
 */
export const MoleculeScene: React.FC<{ visual: MoleculeVisual; cues: Record<string, number> }> = ({ visual, cues }) => {
  const frame = useCurrentFrame();
  const appearAt: Record<string, number> = {};
  for (const [cue, atomIds] of Object.entries(visual.reveal ?? {})) {
    for (const id of atomIds) appearAt[id] = Math.min(appearAt[id] ?? Infinity, cues[cue] ?? 0);
  }
  visual.atoms.forEach((atom, i) => {
    appearAt[atom.id] ??= 12 + i * 6;
  });
  const allShown = Math.max(...Object.values(appearAt));

  const xs = visual.atoms.map((a) => a.x);
  const ys = visual.atoms.map((a) => a.y);
  const margin = 90;
  const spanX = Math.max(...xs) - Math.min(...xs) || 1;
  const spanY = Math.max(...ys) - Math.min(...ys) || 1;
  const scale = Math.min((W - 2 * margin) / spanX, (H - 2 * margin) / spanY, 330);
  const midX = (Math.max(...xs) + Math.min(...xs)) / 2;
  const midY = (Math.max(...ys) + Math.min(...ys)) / 2;
  const pos = (id: string) => {
    const atom = visual.atoms.find((a) => a.id === id);
    return { x: W / 2 + ((atom?.x ?? 0) - midX) * scale, y: H / 2 + ((atom?.y ?? 0) - midY) * scale };
  };

  return (
    <VisualArea>
      <VisualTitle>{visual.title}</VisualTitle>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ marginTop: 10 }}>
        {visual.bonds.map((bond) => {
          const a = pos(bond.from);
          const b = pos(bond.to);
          const start = Math.max(appearAt[bond.from], appearAt[bond.to]) + 6;
          const length = Math.hypot(b.x - a.x, b.y - a.y);
          const order = bond.order ?? 1;
          const nx = (-(b.y - a.y) / length) * 14;
          const ny = ((b.x - a.x) / length) * 14;
          return Array.from({ length: order }, (_, k) => {
            const shift = k - (order - 1) / 2;
            return (
              <line
                key={`${bond.from}-${bond.to}-${k}`}
                x1={a.x + nx * shift}
                y1={a.y + ny * shift}
                x2={b.x + nx * shift}
                y2={b.y + ny * shift}
                stroke={COLORS.text}
                strokeOpacity={0.85}
                strokeWidth={12}
                strokeLinecap="round"
                strokeDasharray={length}
                strokeDashoffset={length * (1 - progress(frame, start, 14))}
              />
            );
          });
        })}
        {visual.atoms.map((atom) => {
          const { x, y } = pos(atom.id);
          const r = radiusOf(atom.element);
          const shown = pop(frame, appearAt[atom.id], 18);
          const ring = progress(frame, appearAt[atom.id], 22);
          const fill = ELEMENT_COLORS[atom.element] ?? COLORS.accent3;
          return (
            <g key={atom.id} opacity={Math.min(1, shown * 1.4)}>
              <circle cx={x} cy={y} r={r * (1 + ring * 0.7)} fill="none" stroke={fill} strokeWidth={6} opacity={(1 - ring) * 0.8} />
              <circle cx={x} cy={y} r={Math.max(0.01, r * shown)} fill={fill} />
              <text
                x={x}
                y={y + r * 0.34}
                textAnchor="middle"
                fontFamily="Kanit"
                fontWeight={800}
                fontSize={r * 0.95}
                fill={LIGHT_ELEMENTS.has(atom.element) ? COLORS.background : COLORS.text}
                opacity={shown}
              >
                {atom.label ?? atom.element}
              </text>
            </g>
          );
        })}
      </svg>
      {visual.formula ? (
        <Formula
          formula={visual.formula}
          style={{ fontFamily: HEADING_FONT, fontWeight: 800, fontSize: 96, color: COLORS.accent, textAlign: "center", opacity: progress(frame, allShown + 10, 12) }}
        />
      ) : null}
      {visual.caption ? (
        <div style={{ marginTop: 6, textAlign: "center", fontFamily: BODY_FONT, fontWeight: 600, fontSize: 44, color: COLORS.muted, opacity: progress(frame, allShown + 16, 12) }}>
          {visual.caption}
        </div>
      ) : null}
    </VisualArea>
  );
};
