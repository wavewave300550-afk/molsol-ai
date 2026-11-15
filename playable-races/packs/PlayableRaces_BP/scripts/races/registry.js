import { golem } from "./golem.js";
import { jackalope } from "./jackalope.js";
import { salamander } from "./salamander.js";
export const RACES = [salamander, golem, jackalope];
const byCode = new Map(RACES.map((r) => [r.code, r]));
const byKey = new Map(RACES.map((r) => [r.key, r]));
export function raceByCode(code) {
    return byCode.get(code);
}
export function raceByKey(key) {
    return byKey.get(key) ?? byCode.get(key);
}
export function raceByFocus(itemId) {
    return RACES.find((r) => r.focusItem === itemId);
}
