import type { Cast } from "./context";
import type { Routine } from "../core/tasks";
import { COLORS } from "../core/fx";

/** Temporary marker used only while a spell's real implementation is being built. */
export function* placeholder(c: Cast): Routine {
  const col = c.spell.school === "pressure" ? COLORS.orange : c.spell.school === "ice" ? COLORS.ice : COLORS.crimson;
  c.particle(`grimoire:${c.spell.school}_charge`, c.origin, { color: col, size: 1, radius: 1 });
  yield 1;
}
