import { system } from "@minecraft/server";
import { PROP_SKILL, SKILLS } from "./config.js";
const states = new Map();
export const now = () => system.currentTick;
export function state(p) {
    let s = states.get(p.id);
    if (!s) {
        let skill = 0;
        try {
            const saved = p.getDynamicProperty(PROP_SKILL);
            if (typeof saved === "number" && saved >= 0 && saved < SKILLS.length)
                skill = Math.floor(saved);
        }
        catch {
            // keep default
        }
        s = {
            skill,
            readyAt: SKILLS.map(() => 0),
            lastUse: -100,
            parity: 0,
            busyUntil: 0,
            flashUntil: 0,
            flashText: "",
            willUntil: 0,
            willTier: 0,
            nextPulse: 0,
            ultUntil: 0,
        };
        states.set(p.id, s);
    }
    return s;
}
export const dropState = (id) => states.delete(id);
export const fxEntities = new Map();
