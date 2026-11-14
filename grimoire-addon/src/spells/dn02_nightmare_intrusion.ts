import { Entity, Vector3 } from "@minecraft/server";
import { DN02 as C } from "../config/dn02";
import { defineSpell } from "../core/registry";
import { damage, drag, effect, knockback, restrain } from "../lib/combat";
import { burst, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { add, distXZ, flat, len, lerp, mul, norm, right, smooth, sub, up, yawOf } from "../lib/vec";

// Animation states (tools/assets/dn_guest.py DOOR_STATES / GUEST_STATES)
const DOOR = { hidden: 0, manifest: 1, closed: 2, handle: 3, open: 4, held: 5, slam: 6, vanish: 7 };
const GUEST = { hidden: 0, emerge: 1, reach: 2, grab: 3, pull: 4, withdraw: 5, miss: 6 };

// Animation lengths in ticks (DOOR_LEN / GUEST_LEN in dn_guest.py x 20)
const A = { manifest: 24, handle: 28, open: 24, slamShut: 3, vanish: 20, emerge: 52, reach: 24, grab: 12, pull: 32, withdraw: 22 };

// Timeline (ticks).  The script follows the animations exactly; there is no way to read animation progress.
// Everything up to the Guest leaning out is fixed; what follows depends on whether anyone is in reach.
const T_CLOSED = A.manifest;                 // frame assembled, door unfolded from its hinge
const T_HANDLE = T_CLOSED + 6;               // the dread beat: the handle turns by itself
const T_OPEN = T_HANDLE + A.handle;          // latch gives, the door creaks open on the corridor
const T_EMERGE = T_OPEN + 6;                 // something comes up the corridor
const T_HELD = T_OPEN + A.open;
const T_REACH = T_EMERGE + A.emerge;         // it has leaned out: is anyone there?

/**
 * DN02 - Nightmare Intrusion: The Guest Behind the Door.
 * An antique bedroom door assembles behind the target with no wall to hold it.  Its handle turns,
 * it opens on an impossibly long corridor, and the Guest comes up it and leans out.
 *   Someone in reach: the arms grow, seize that enemy (real restraint + squeeze damage), drag it to
 *     the threshold, let go -- and the door slams shut on the world with a devastating impact.
 *   Nobody in reach: the Guest waits at the threshold for a moment.  If an enemy comes close it is
 *     taken; otherwise the Guest goes back inside and the door closes quietly.  It never mimes a grab
 *     at empty air.
 */
export default defineSpell("dn02", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center, target } = focus(caster, aim, C.snapRadius);
  let victim: Entity | undefined = target && isAlive(target) ? target : undefined;
  const spot = victim ? groundBelow(dim, victim.location) : center;

  // door stands behind the victim, facing the caster
  let dir = flat(sub(spot, caster.location));
  dir = len(dir) < 0.5 ? aim.forward : norm(dir);
  const door = groundBelow(dim, add(spot, mul(dir, C.standoff)));
  const facing = mul(dir, -1);
  const yaw = yawOf(facing);
  const rgt = right(facing);
  /** Door-local model units (1/16 block, -z = in front of the door) -> world. */
  const L = (x: number, y: number, z: number): Vector3 => add(add(up(door, y / 16), mul(facing, -z / 16)), mul(rgt, x / 16));
  const gripAt = L(0, 0, -C.standoff * 16);
  const dragEnd = L(0, 0, -C.pullStop * 16);
  const keyhole = L(-14, 32.6, -2.5);
  const lights = blocksFor(scene);

  // -- manifestation (telegraph where the slam will land)
  const d = scene.spawn("dn_guest_door", door, { yaw, state: DOOR.manifest, skin: 0 });
  const warn = scene.spawn("telegraph", up(dragEnd, 0.05), { kind: 1, size: C.slamRadius, state: 4 });
  scene.at(40, () => warn.state(2));
  sound(dim, "dn_guest_manifest", door, 1.1);
  burst(dim, "dn_guest_mote", L(0, 44, 0), 2.2, 6);
  scene.at(6, () => particle(dim, "dn_guest_dust", up(door, 0.2)));
  scene.at(14, () => burst(dim, "dn_guest_scrap", L(0, 82, -2), 1.2, 3));
  scene.at(T_CLOSED, () => d.state(DOOR.closed));

  // -- the dread beat: the handle turns slowly, rattles, the latch gives
  scene.at(T_HANDLE, () => {
    d.state(DOOR.handle);
    sound(dim, "dn_guest_handle", keyhole, 1.0);
    if (victim && isAlive(victim)) effect(victim, "slowness", T_REACH - T_HANDLE, C.dreadSlowAmp);
  });
  scene.at(T_HANDLE + 4, () => particle(dim, "dn_guest_mote", keyhole));
  scene.at(T_HANDLE + 22, () => particle(dim, "dn_guest_cracklight", L(-14, 32, -2)));

  // -- the door opens on the corridor; cold lamplight spills out
  scene.at(T_OPEN, () => {
    d.state(DOOR.open);
    sound(dim, "dn_guest_creak", door, 1.1);
    lights.place(L(0, 40, -12), LIGHT);
    particle(dim, "dn_guest_dust", L(0, 2, -6));
  });
  scene.at(T_OPEN + 8, () => sound(dim, "dn_guest_drone", L(0, 30, 6), 1.0));
  let lamps = true;
  scene.every(7, () => { if (lamps && d.valid) particle(dim, "dn_guest_lamp", L(0, 36, -3)); }, T_OPEN + 10, T_REACH + 200);
  scene.at(T_HELD, () => d.state(DOOR.held));

  // -- the Guest comes up the corridor, grips the frame, leans out
  let guest: Actor | undefined;
  scene.at(T_EMERGE, () => {
    guest = scene.spawn("dn_guest", door, { yaw, state: GUEST.emerge });
    sound(dim, "dn_guest_approach", L(0, 30, 10), 1.0);
  });
  scene.at(T_EMERGE + 29, () => { sound(dim, "dn_guest_clicks", L(-20, 50, -4), 1.0); particle(dim, "dn_guest_dust", L(-20, 52, -5)); });
  scene.at(T_EMERGE + 40, () => { sound(dim, "dn_guest_voice", L(-20, 70, -14), 1.0); particle(dim, "dn_guest_breath", L(-24, 70, -22)); });

  // -- leaned out.  Who is actually standing there?
  const inReach = (e: Entity): boolean => distXZ(e.location, gripAt) <= C.reachRadius && Math.abs(e.location.y - door.y) <= 5;
  const pick = (): Entity | undefined => {
    if (victim && isAlive(victim) && inReach(victim)) return victim;
    return hostiles(dim, gripAt, C.reachRadius, caster).find(inReach);
  };
  let decided = false;
  const deadline = T_REACH + secs(C.waitSeconds);
  scene.every(4, () => {
    if (decided) return;
    const v = pick();
    if (v) { decided = true; victim = v; take(scene.tick, v); } else if (scene.tick >= deadline) { decided = true; goBack(scene.tick); }
  }, T_REACH, deadline + 5);
  // while it waits: breath and clicks from the doorway, nothing else
  scene.every(22, () => { if (!decided) { sound(dim, "dn_guest_clicks", L(-20, 50, -4), 0.8, 0.9); particle(dim, "dn_guest_breath", L(-24, 70, -22)); } }, T_REACH + 10, deadline);

  /** Nobody came: the Guest draws back into the corridor and the door shuts without violence. */
  function goBack(t0: number): void {
    guest?.state(GUEST.withdraw);
    sound(dim, "dn_guest_clicks", L(0, 40, -6), 0.9, 1.35);
    warn.state(3);
    scene.at(t0 + 8, () => scene.despawn(warn));
    scene.at(t0 + A.withdraw, () => { if (guest) scene.despawn(guest); });
    scene.at(t0 + A.withdraw + 2, () => { lamps = false; d.state(DOOR.slam); sound(dim, "dn_guest_slam", L(0, 40, -2), 0.7, 1.2); });
    scene.at(t0 + A.withdraw + 2 + A.slamShut, () => { lights.remove(L(0, 40, -12)); particle(dim, "dn_guest_dust", L(0, 2, -4)); });
    vanishAt(t0 + A.withdraw + 2 + A.slamShut + 14);
  }

  /** Someone is there: reach, seize, drag to the threshold, let go, SLAM. */
  function take(t0: number, v: Entity): void {
    const tGrab = t0 + A.reach, tGrip = tGrab + 2, tPull = tGrab + A.grab, tWithdraw = tPull + A.pull;
    const tSlam = tWithdraw + 5, tImpact = tSlam + A.slamShut;
    let caught = false;
    let release: (() => void) | undefined;
    // reach: the arms rise and keep growing
    guest?.state(GUEST.reach);
    sound(dim, "dn_guest_voice", L(0, 74, -30), 1.1, 0.9);
    effect(v, "slowness", A.reach + 4, C.reachSlowAmp);
    scene.at(t0 + 10, () => sound(dim, "dn_guest_clicks", L(0, 50, -30), 1.0, 1.2));
    // the hands close
    scene.at(tGrab, () => {
      caught = isAlive(v) && distXZ(v.location, gripAt) <= C.reachRadius + 1.5;
      guest?.state(caught ? GUEST.grab : GUEST.withdraw);
      if (!caught) { decided = true; goBackAfterMiss(tGrab); }
    });
    scene.at(tGrip, () => {
      if (!caught || !isAlive(v)) { caught = false; return; }
      const from = { ...v.location };
      const anchor = { x: gripAt.x, y: v.location.y, z: gripAt.z };
      const end = { x: dragEnd.x, y: v.location.y, z: dragEnd.z };
      // real restraint until the slam (released automatically if the scene ends)
      release = restrain(scene, v, tImpact - tGrip, anchor);
      // the hands carry it: registered after restrain() so this position wins each tick
      scene.every(1, () => {
        if (!isAlive(v)) return;
        const t = scene.tick;
        if (t < tPull) { drag(v, lerp(from, anchor, smooth((t - tGrip) / 6))); return; }
        drag(v, lerp(anchor, end, smooth((t - tPull) / (A.pull - 1))));
        if (t < tWithdraw && (t - tPull) % 3 === 0) particle(dim, "dn_guest_drag", v.location);
      }, tGrip, tImpact);
      sound(dim, "dn_guest_grab", v.location, 1.1);
      particle(dim, "dn_guest_grip", up(v.location, 1));
      particle(dim, "dn_guest_squeeze", up(v.location, 1));
      scene.every(C.squeezeEvery, () => {
        if (!isAlive(v)) return;
        damage(v, C.squeezeDamage, caster);
        particle(dim, "dn_guest_squeeze", up(v.location, 1.1));
      }, tGrip + 4, tImpact);
    });
    // pull toward the threshold
    scene.at(tPull, () => {
      if (!caught) return;
      guest?.state(GUEST.pull);
      sound(dim, "dn_guest_drag", isAlive(v) ? v.location : gripAt, 1.0);
    });
    // let go, withdraw, SLAM
    scene.at(tWithdraw, () => {
      if (!caught) return;
      guest?.state(GUEST.withdraw);
      sound(dim, "dn_guest_clicks", L(0, 40, -6), 1.0, 1.35);
    });
    scene.at(tSlam, () => {
      if (!caught) return;
      lamps = false;
      d.state(DOOR.slam);
      sound(dim, "dn_guest_slam", L(0, 40, -2), 1.8);
    });
    scene.at(tImpact, () => {
      if (!caught) return;
      release?.();
      d.skin(1); // the paint splits, the lamps die
      lights.remove(L(0, 40, -12));
      warn.state(3);
      scene.after(8, () => scene.despawn(warn));
      // shock visuals
      particle(dim, "dn_guest_shock", up(dragEnd, 0.15));
      particle(dim, "dn_guest_shock_v", L(0, 36, -6));
      particle(dim, "fx_flash", L(0, 40, -4));
      particle(dim, "dn_guest_doors", L(0, 40, -6));
      particle(dim, "dn_guest_splinter", L(0, 44, -3));
      particle(dim, "dn_guest_splinter", L(-10, 20, -3));
      particle(dim, "dn_guest_cracklight", L(0, 40, -2));
      ring(dim, "fx_dust", up(door, 0.2), 1.6, 6);
      burst(dim, "dn_guest_scrap", L(0, 60, -4), 2, 5);
      // damage: everything at the threshold, plus the finisher for the one the Guest held
      for (const e of hostiles(dim, dragEnd, C.slamRadius, caster)) {
        damage(e, C.slamDamage + (e.id === v.id ? C.finisherBonus : 0), caster);
        knockback(e, door, C.slamKnock, C.slamLift);
      }
      scene.after(8, () => { if (guest) scene.despawn(guest); });
      scene.after(6, () => particle(dim, "dn_guest_dust", L(0, 2, -4)));
      scene.after(12, () => particle(dim, "dn_guest_cracklight", L(0, 40, -2)));
      vanishAt(tImpact + 24);
    });
  }
  /** The chosen enemy got away or died while the arms were coming: no mime, straight back inside. */
  function goBackAfterMiss(t0: number): void {
    sound(dim, "dn_guest_voice", L(0, 60, -40), 0.9, 1.15);
    warn.state(3);
    scene.at(t0 + 8, () => scene.despawn(warn));
    scene.at(t0 + A.withdraw, () => { if (guest) scene.despawn(guest); });
    scene.at(t0 + A.withdraw + 2, () => { lamps = false; d.state(DOOR.slam); sound(dim, "dn_guest_slam", L(0, 40, -2), 0.7, 1.2); });
    scene.at(t0 + A.withdraw + 2 + A.slamShut, () => lights.remove(L(0, 40, -12)));
    vanishAt(t0 + A.withdraw + 2 + A.slamShut + 14);
  }

  // -- everything folds flat into the keyhole and is gone
  function vanishAt(t: number): void {
    scene.at(t, () => { d.state(DOOR.vanish); sound(dim, "dn_guest_hush", keyhole, 1.0); });
    scene.at(t + 8, () => particle(dim, "dn_guest_keyhole", keyhole));
    scene.at(t + 17, () => particle(dim, "fx_flash", keyhole));
    scene.at(t + A.vanish, () => scene.despawn(d));
    scene.endAt(t + A.vanish + 4);
  }
  scene.endAt(deadline + 400);   // safety net; the real end is set by vanishAt()
});
