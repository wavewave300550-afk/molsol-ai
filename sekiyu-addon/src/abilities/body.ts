import { Form } from "../config.js";
import { anim } from "../core/fx.js";
import { setForm } from "../logia.js";
import { setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * 2 - Petroleum Body: the Logia transformation. While active:
 *   every physical hit passes through (see logia.ts), moving = light crude (Speed II),
 *   standing = heavy crude (Resistance I), your melee hits flare with controlled fire,
 *   you drip small oil slicks while moving. Use again to reform (no cooldown on reform).
 */
export function castBody(c: Ctx): CastResult {
  const { p, s } = c;
  if (s.form === Form.Dissolved) return "Reform first";
  setForm(p, s, Form.Body);
  anim(p, "melt");
  setActive(s, "Petroleum Body", 60);
  return true;
}

export function reformBody(c: Ctx): void {
  setForm(c.p, c.s, Form.Human);
}
