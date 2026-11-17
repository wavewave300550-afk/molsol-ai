import { Form, TUNING } from "../config.js";
import { anim } from "../core/fx.js";
import { setForm } from "../logia.js";
import { setActive, setFollowUp } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * 7 - Petroleum Infiltration: dissolve into a puddle (3D model replaces the player model) for 3s.
 * Speed IV, Invisibility, physical attacks pass through, seep through 1-block-high gaps
 * (logia.ts trySeep: validated, never through solid blocks or out of the world). Reforms by
 * itself after 3s, or Use again to reform early. Effects are short and removed on reform.
 */
export function castSeep(c: Ctx): CastResult {
  const { p, s } = c;
  if (s.sealed) return "Submerged - cannot dissolve";
  setForm(p, s, Form.Dissolved);
  anim(p, "melt");
  setActive(s, "Infiltration", TUNING.seep.duration);
  setFollowUp(s, "seep", TUNING.seep.duration, () => setForm(p, s, Form.Human));
  return true;
}
