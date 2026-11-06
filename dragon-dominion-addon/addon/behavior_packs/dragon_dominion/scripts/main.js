// Dragon Dominion - entry point.
// core/      reusable boss framework (registry, combat rules, terrain queries, effects)
// dragons/   one folder per dragon species; each registers itself with the registry
import { registerBoss } from "./core/registry.js";
import { GHARVOK_ID } from "./dragons/gharvok/config.js";
import { Gharvok } from "./dragons/gharvok/gharvok.js";
import { initSummon } from "./dragons/gharvok/summon.js";

registerBoss(GHARVOK_ID, (entity) => new Gharvok(entity));
initSummon();
