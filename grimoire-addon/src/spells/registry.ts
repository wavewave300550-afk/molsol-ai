import { BLOOD } from "./blood";
import { ICE } from "./ice";
import { PRESSURE } from "./pressure";
import { SCHOOLS, School, SpellDef } from "./types";

const BY_SCHOOL: Record<School, SpellDef[]> = { pressure: PRESSURE, ice: ICE, blood: BLOOD };
const BY_ID = new Map<string, SpellDef>();

for (const s of SCHOOLS) {
  const list = BY_SCHOOL[s];
  if (list.length !== 15) throw new Error(`${s} grimoire must contain exactly 15 spells, has ${list.length}`);
  list.forEach((sp, i) => {
    if (sp.school !== s) throw new Error(`${sp.code} is registered in the wrong grimoire`);
    const expected = `${s[0].toUpperCase()}${String(i + 1).padStart(2, "0")}`;
    if (sp.code !== expected) throw new Error(`spell order mismatch: ${sp.code} at position ${expected}`);
    if (BY_ID.has(sp.id)) throw new Error(`duplicate spell id ${sp.id}`);
    BY_ID.set(sp.id, sp);
  });
}

export function spellAt(school: School, index: number): SpellDef {
  const list = BY_SCHOOL[school];
  return list[((index % 15) + 15) % 15];
}

export function spellById(id: string): SpellDef | undefined {
  return BY_ID.get(id);
}

export function allSpells(): SpellDef[] {
  return [...PRESSURE, ...ICE, ...BLOOD];
}

export function spellsOf(school: School): SpellDef[] {
  return BY_SCHOOL[school];
}
