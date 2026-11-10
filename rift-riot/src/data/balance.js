// ─────────────────────────────────────────────────────────────────────────────
// RIFT RIOT — ค่าปรับสมดุลทั้งหมดอยู่ที่ไฟล์นี้ไฟล์เดียว
// All tunable gameplay numbers live here. Units: metres, seconds, radians.
// ─────────────────────────────────────────────────────────────────────────────

export const BALANCE = {
  race: {
    laps: 3,
    racerCount: 6,
    countdown: 3.0, // seconds of 3-2-1 before GO
    fixedDt: 1 / 60, // simulation step (frame-rate independent)
    maxStepsPerFrame: 5, // spiral-of-death guard when the frame rate collapses
    finishTimeout: 60, // seconds the rest of the field may keep racing after the player finishes
    playerGridSlot: 3, // 0 = pole … 5 = last
  },

  vehicle: {
    maxSpeed: 34, // m/s, shared baseline top speed
    accel: 15, // m/s²
    brake: 36,
    reverseSpeed: 8,
    coastDrag: 6, // deceleration with no throttle
    turnLow: 2.3, // rad/s yaw authority at low speed
    turnHigh: 0.9, // rad/s yaw authority at top speed
    turnRampSpeed: 4, // below this speed steering fades out (no spinning on the spot)
    steerSmoothing: 14, // 1/s — how fast the steering input reaches its target
    grip: 7.5, // 1/s — how fast velocity realigns with heading
    radius: 1.5, // shared collision radius (fair for every silhouette)
    standardLength: 4, // "one racer length" used by skill radii
    gravity: 32,
    wallBounce: 0.25,
    wallScrub: 0.38, // share of speed lost on a square wall hit
    wallAlign: 2.6, // rad/s: a scraped wall turns you along it instead of pinning you
    airControl: 0.3, // steering authority while airborne
    bumpRestitution: 0.35,
  },

  drift: {
    minSpeed: 14, // must be going at least this fast to start / keep a drift
    turnMul: 1.5, // yaw authority multiplier while drifting
    grip: 2.6, // lowered grip → visible slide
    innerSteer: 1.0, // steering into the drift
    outerSteer: 0.28, // counter-steering still keeps some rotation
    carry: 0.8, // share of scrubbed sideways speed kept as forward speed while drifting
    chargeTime: 0.9, // continuous drift needed before a boost is earned
    minSlip: 0.12, // rad — must actually be sliding for charge to count
    boostTime: 0.5,
    boostSpeedMul: 1.16,
    boostAccel: 34,
  },

  // Central anti-juggle rules (apply to everyone, not a per-character perk)
  push: {
    globalLock: 0.4, // min seconds between two pushes on the same target, any source
    maxKnock: 17, // cap of accumulated knock velocity (m/s)
    decay: 4.2, // 1/s exponential decay of knock velocity
    verticalReach: 2.4, // pushes ignore targets further apart vertically than this
  },

  slick: {
    grip: 0.9, // grip while on a slick patch
    steerMul: 0.72, // steering authority on slick
    recoverTime: 0.6, // seconds to blend back to normal after leaving
    groundTolerance: 0.45, // must be this close to the ground to be affected
  },

  respawn: {
    killDepth: 14, // metres below the road before a fall counts
    delay: 1.1, // seconds between detection and being placed back
    backOff: 8, // metres behind the last safe spot (never forward)
    grace: 1.4, // seconds of push immunity + blink after returning
    stuckSpeed: 1.6,
    stuckTime: 3.2, // throttle held but not moving for this long → return
    outOfBounds: 95, // metres from any road → return
  },

  skills: {
    railMaker: {
      duration: 4.0,
      cooldown: 20,
      height: 0.7, // rail rides this far above the ground
      turnMul: 0.5, // rails cannot kink: reduced yaw authority
      minSpeedMul: 0.72, // the handcar keeps rolling on rail
      fadeTime: 0.45, // rail dissolve after the skill ends
      pieceSpacing: 1.6,
      previewLength: 16,
    },
    tantrum: {
      cooldown: 16,
      windup: 0.2,
      radiusLengths: 2.5, // × standardLength
      strength: 21, // knock velocity (m/s) before stability
      recover: 0.35, // short pose after the scream
    },
    pirouette: {
      duration: 3.0,
      cooldown: 18,
      speedMul: 1.25,
      accel: 30,
      turnMul: 0.9,
      gripMul: 1.25,
    },
    slingshot: {
      cooldown: 18,
      windup: 0.25,
      airTime: 1.2,
      gravity: 24, // jump-specific gravity → apex ≈ 4.3 m
      minSpeedMul: 0.86, // launch never slower than this share of top speed
      airControl: 0.35,
    },
    eternalLove: {
      duration: 4.0,
      cooldown: 20,
      patchLife: 3.0,
      patchRadius: 3.1,
      patchSpacing: 3.4, // metres travelled between two patches
      maxPatches: 48,
    },
    hurricane: {
      duration: 4.0,
      cooldown: 20,
      radius: 6.6, // smaller than the tantrum wave (10 m)
      strength: 12.5,
      perTargetInterval: 0.9,
      ownerGripMul: 0.62,
      ownerTurnMul: 0.86,
    },
  },

  track: {
    sampleStep: 2,
    bridge: {
      period: 14, // full open/close cycle of the shortcut span
      solidTime: 6.5, // span is drivable from 0 … solidTime
      warnTime: 1.6, // blinking warning before it vanishes
      gapLength: 24,
    },
    teacup: { radius: 2.3, height: 2.7, hitSpeedMul: 0.55, hitKnock: 7, hitLock: 0.6 },
  },

  ai: {
    lookBase: 9,
    lookPerSpeed: 0.5,
    steerGain: 2.6,
    cornerSafety: 0.9, // share of theoretical cornering yaw the AI plans with
    brakeDecel: 20,
    laneWander: 2.6,
    reactionMin: 0.15,
    reactionMax: 0.55,
    skillLevels: [0.99, 0.975, 0.96, 0.945, 0.93], // per-AI share of full pace (fixed for the race, no rubber banding)
  },

  camera: {
    distance: 9.2,
    height: 4.3,
    lookAhead: 7,
    fov: 62,
    boostFov: 9,
    yawFollow: 5.5,
    posFollow: 9,
  },
};

export default BALANCE;
