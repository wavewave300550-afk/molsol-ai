/**
 * Global gameplay configuration.  Every value here is safe to edit; rebuild with
 * `npm run bundle` afterwards.  Per-spell numbers live in src/config/<spell id>.ts.
 * Cooldowns are NOT here on purpose: they are the approved registry in core/registry.ts.
 */
export const CONFIG = {
  /** Give every player the three Grimoires the first time they join a world with the add-on. */
  starterKit: true,
  input: {
    /** Minimum ticks Use must be held before a release counts as a cast (20 ticks = 1 s). */
    minHoldTicks: 6,
    /** Ticks after a cast/cancel during which a new hold is ignored (guards duplicate callbacks). */
    rearmTicks: 2,
    /**
     * Compatibility fallback, OFF by default.  If a platform never raises itemStartUse for the
     * Grimoire, hold/release can be inferred from the repeating itemUse heartbeat instead.
     * Toggle in game with:  /scriptevent grimoire:config heartbeat on|off
     */
    heartbeatFallback: false,
    heartbeatGapTicks: 7,
  },
  hud: {
    /** Ticks between action-bar refreshes while a Grimoire is held. */
    refreshTicks: 10,
  },
  targeting: {
    /** Entity families treated as hostile spell targets. */
    hostileFamilies: ["monster"] as string[],
    /** Any entity carrying this tag is also treated as hostile (handy for test dummies). */
    testTag: "grimoire_target",
    /** When true other players are hostile targets instead of allies. */
    pvp: false,
    /** How far the caster's aim ray reaches when picking a target point. */
    aimRange: 40,
    /** A spell is never centred closer to its caster than this (blocks), e.g. when looking at your feet. */
    minAimDistance: 9,
    /** Hard cap on targets a single query returns. */
    maxTargets: 24,
  },
  limits: {
    /** Maximum spell entities alive at once across the whole world. */
    maxActors: 220,
    /** Maximum temporary blocks (barriers / lights) alive at once. */
    maxTempBlocks: 1400,
    /** Maximum script-spawned particles per tick. */
    maxParticlesPerTick: 90,
    /** Maximum natural ground blocks (and the plants above them) a spell may hold changed at once, world-wide. */
    maxGroundBlocks: 3000,
  },
  /**
   * Temporary living ground (src/lib/terraform.ts): block changes and chunk sections (each one a mesh the
   * client rebuilds) per pulse, ticks between the pulses of one sweep; one pulse a tick world-wide.
   */
  ground: {
    perPulse: 80,
    maxSections: 4,
    every: 4,
  },
  /** Spell fog and time of day (src/lib/atmos.ts). */
  atmosphere: {
    /** Per-player spell fog. */
    fog: true,
    /** Players this close to the caster see the spell's fog too. */
    fogRadius: 48,
    /** "auto": a spell may move the world's time of day while every other player is within timeRadius; "off": never. */
    time: "auto" as "auto" | "off",
    timeRadius: 128,
  },
  /** Short cinematic camera shots for the caster (src/lib/cinema.ts). */
  cinematic: {
    enabled: true,
    maxShots: 4,
    maxSeconds: 4,
    /** No shot below this fraction of health, or with an enemy within clearRadius blocks. */
    minHealth: 0.4,
    clearRadius: 5,
  },
};

/** Same object; the name signals intentional runtime mutation (/scriptevent grimoire:config ...). */
export const RUNTIME = CONFIG;
