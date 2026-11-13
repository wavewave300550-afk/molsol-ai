/**
 * Global gameplay configuration.  Every value here is safe to edit; rebuild with
 * `npm run bundle` afterwards.  Per-spell numbers live in src/config/<spell id>.ts.
 * Cooldowns are NOT here on purpose: they are the approved registry in core/registry.ts.
 */
export const CONFIG = {
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
  },
};

/** Same object; the name signals intentional runtime mutation (/scriptevent grimoire:config ...). */
export const RUNTIME = CONFIG;
