import { AbilityId } from "../config.js";
import { castBoost } from "./boost.js";
import { castCannon } from "./cannon.js";
import { castDash } from "./dash.js";
import { castJump } from "./jump.js";
import { castKick } from "./kick.js";
import { castKnuckle } from "./knuckle.js";
import { castMist } from "./mist.js";
import { castRedline } from "./redline.js";
import { castScald } from "./scald.js";
import { Cast } from "./types.js";

export const CASTS: Record<AbilityId, Cast> = {
  boost: castBoost,
  dash: castDash,
  jump: castJump,
  cannon: castCannon,
  scald: castScald,
  knuckle: castKnuckle,
  kick: castKick,
  mist: castMist,
  redline: castRedline,
};
