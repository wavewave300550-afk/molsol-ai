/**
 * Race registry.  Permanent codes: 001 Salamander, 002 Golem, 003 Jackalope,
 * 004 Xenentoma, 005 Flying Spaghetti Monster, 006 Nurariten (Unique).
 * Future releases add races 004+ by creating a RaceDef module and listing it here;
 * nothing else in the framework needs to change.
 */
import { golem } from "./golem.js";
import { jackalope } from "./jackalope.js";
import { salamander } from "./salamander.js";
import { spaghetti } from "./spaghetti.js";
import { RaceDef } from "./types.js";
import { xenentoma } from "./xenentoma.js";

export const RACES: RaceDef[] = [salamander, golem, jackalope, xenentoma, spaghetti];

const byCode = new Map(RACES.map((r) => [r.code, r]));
const byKey = new Map(RACES.map((r) => [r.key, r]));

export function raceByCode(code: string): RaceDef | undefined {
  return byCode.get(code);
}

export function raceByKey(key: string): RaceDef | undefined {
  return byKey.get(key) ?? byCode.get(key);
}

export function raceByFocus(itemId: string): RaceDef | undefined {
  return RACES.find((r) => r.focusItem === itemId);
}
