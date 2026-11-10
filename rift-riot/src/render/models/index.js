import { buildBoonsong } from './boonsong.js';
import { buildBaby } from './baby.js';
import { buildCelestine } from './celestine.js';
import { buildGranny } from './granny.js';
import { buildLovers } from './lovers.js';
import { buildGator } from './gator.js';

// id → builder. Adding a racer = one entry here + data in racers.js + a skill.
export const MODEL_BUILDERS = {
  boonsong: buildBoonsong,
  baby: buildBaby,
  celestine: buildCelestine,
  granny: buildGranny,
  lovers: buildLovers,
  gator: buildGator,
};
