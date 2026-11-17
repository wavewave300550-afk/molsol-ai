/** DN03 House of Shifting Sleep -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DN03 = {
  // ---- the maze grid (centred on the fight, pushed away from the caster so the caster starts outside it)
  /** Cells per side of the square grid. 6 cells x 4 blocks = 24 blocks across. */
  gridCells: 6,
  /** Cell size in blocks (must be even: a door is the middle column of a wall). One wall segment spans one cell side. */
  cellSize: 4,
  /** Gap kept between the caster and the grid edge when the grid is placed. */
  casterMargin: 2,
  /** Maximum distance the grid may be pushed away from the aimed point to leave the caster outside. */
  maxGridShift: 10,
  /** Ground under a column may differ from the grid's ground by this much before the column is skipped. */
  maxColumnStep: 3,

  // ---- wall segments
  /** Wall-segment actors that make up the maze (also the number of walls in every layout). */
  wallCount: 18,
  /** Height of the barrier collision under each wall (players cannot jump 3, mobs cannot climb it). */
  wallBlocks: 3,

  // ---- timing (ticks)
  /** Active battlefield-control duration: from the first layout to the fold-back (12 s). */
  activeTicks: 240,
  /** The house rearranges its layout this often while active (2.5 s). */
  shiftEvery: 50,
  /** At most this many walls travel per rearrangement (the rest stay, so the change stays readable). */
  maxMovesPerShift: 8,
  /** Delay between successive walls starting to move in one rearrangement. */
  moveStagger: 2,
  /** Chalk lines appear where a wall will arrive this many ticks before it starts moving. */
  telegraphTicks: 10,

  // ---- layout logic weights (higher = more likely to get a wall)
  score: {
    /** Wall between two cells that belong to different hostile groups (splits the pack). */
    separate: 10,
    /** Wall on the side of a hostile's cell that faces the caster (forces a detour away from the caster). */
    blockApproach: 6,
    /** Side walls of the controllable corridor that leads away from the caster. */
    corridor: 5,
    /** Outer edge on the caster's side of the maze (a front line between caster and enemies). */
    frontLine: 3,
    /** Any other outer edge. */
    perimeter: 1,
    /** Edge next to a cell holding a player (allowed only as a door). */
    nearAlly: -2,
    /** Random variation per rearrangement so the house never repeats itself exactly. */
    jitter: 3,
  },
  /** Length of the controllable corridor in cells; its far end is the looping door. */
  routeLen: 3,
  /** Hostile groups the layout tries to keep apart. */
  maxGroups: 3,
  /** Search radius for hostiles around the grid centre. */
  radius: 20,

  // ---- collision safety
  /** No new wall may arrive on a column within this distance (blocks) of a player. */
  playerClear: 1.0,
  /** A column is "occupied" (barrier deferred) while any creature stands this close to its centre. */
  occupyRadius: 0.8,
  /** Push given to enemies standing where a wall is arriving (horizontal, vertical). */
  pushH: 0.7,
  pushV: 0.3,
  /** Deferred barrier columns are retried this often. */
  retryEvery: 4,

  // ---- the corridor that loops unexpectedly
  /** Enemies this close to the looping door's gap are carried back to the corridor's start. */
  loopRadius: 1.1,
  /** One loop per enemy at most this often. */
  loopCooldown: 30,
  /** Disorientation after being looped: slowness ticks. */
  loopSlowTicks: 30,

  // ---- living furniture (light control, this is not a damage spell)
  /** The breathing bed makes nearby enemies drowsy: radius, slowness amplifier and ticks. */
  bedRadius: 3,
  bedSlowAmp: 1,
  bedSlowTicks: 40,
  /** The thirteen-hour clock drags time around it: radius and slowness ticks (amplifier 0). */
  clockRadius: 3.5,
  clockSlowTicks: 30,
  /** The chandelier drops its crystals once per rearrangement: blast radius and damage. */
  crystalRadius: 1.8,
  crystalDamage: 4,
  /** The upside-down table bumps enemies it scuttles into: reach, damage and push. */
  tableRadius: 1.4,
  tableDamage: 2,
  tablePush: 0.8,

  // ---- the house itself
  /** Height of the opened house above the maze while it rearranges the battlefield. */
  hoverHeight: 11,
};
