import { HEAT, Mode, TUNING } from "../config.js";
import { enemiesNear, knockFrom } from "../core/combat.js";
import { addTask } from "../core/tasks.js";
import { add, v } from "../core/vec.js";
import { anim, chest, P, particle, S, shake, sized, sound } from "../core/fx.js";
import { setMode } from "../modes.js";
import { isOverheated, now, setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * Ability 9 - Redline Activation: a 0.8s ignition (pressure build-up), then REDLINE for 12s.
 * Redline idles at +4 heat/s and multiplies ability heat by 1.9, so it cannot dodge Overheat;
 * overheating cancels it immediately.
 */
export function castRedline(c: Ctx): CastResult {
  const { p, s, dim } = c;
  const T = TUNING.redline;
  if (s.mode === Mode.Redline) return "Already in REDLINE";
  if (s.igniting) return "Ignition already in progress";
  if (s.heat >= HEAT.max - 12) return "Too hot to ignite Redline - vent first";
  s.igniting = true;
  setActive(s, "Redline ignition", T.ignition);
  anim(p, "ignite");
  sound(dim, S.redlineCharge, p.location, 1.1, 1);
  shake(p, 0.12, T.ignition / 20);
  addTask("redline_ignition", (age) => {
    if (!p.isValid) return false;
    if (!s.igniting || isOverheated(s)) {
      s.igniting = false;
      return false;
    }
    if (age % 2 === 0) particle(dim, P.igniteSwirl, add(p.location, v(0, 0.1, 0)));
    if (age === Math.floor(T.ignition / 2)) sized(dim, P.ring, add(p.location, v(0, 0.1, 0)), 1.0);
    if (age < T.ignition) return true;
    s.igniting = false;
    if (!setMode(p, s, Mode.Redline, { silent: true })) return false;
    s.redlineUntil = now() + T.duration;
    setActive(s, "REDLINE", T.duration);
    particle(dim, P.redlineBurst, p.location);
    particle(dim, P.scaldCloud, chest(p));
    sized(dim, P.ring, add(p.location, v(0, 0.15, 0)), 3.5);
    sound(dim, S.redlineEngage, p.location, 1.4, 1);
    shake(p, 0.45, 0.6);
    // the pressure wave of ignition shoves (but does not hurt) anything close
    for (const e of enemiesNear(dim, p.location, 3.5, p)) knockFrom(e, p.location, 1.6, 0.4);
    p.onScreenDisplay.setTitle("§4§lREDLINE", {
      subtitle: "§cMaximum pressure §7- 12s",
      fadeInDuration: 0,
      stayDuration: 30,
      fadeOutDuration: 10,
    });
    return false;
  });
  return true;
}
