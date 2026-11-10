import { AbilityId } from "../config.js";
import { castBody } from "./body.js";
import { castGeyser } from "./geyser.js";
import { castInferno } from "./inferno.js";
import { castJet } from "./jet.js";
import { castPrison } from "./prison.js";
import { castSeep } from "./seep.js";
import { castSerpent } from "./serpent.js";
import { castTide } from "./tide.js";
import { Cast } from "./types.js";

export const CASTS: Record<AbilityId, Cast> = {
  tide: castTide,
  body: castBody,
  geyser: castGeyser,
  prison: castPrison,
  jet: castJet,
  serpent: castSerpent,
  seep: castSeep,
  inferno: castInferno,
};
