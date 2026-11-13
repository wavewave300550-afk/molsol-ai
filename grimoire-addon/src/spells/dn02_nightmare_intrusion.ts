import { Entity, Vector3 } from "@minecraft/server";
import { DN02 as C } from "../config/dn02";
import { defineSpell } from "../core/registry";
import { damage, drag, effect, knockback, restrain } from "../lib/combat";
import { burst, particle, ring, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { add, distXZ, flat, len, lerp, mul, norm, right, smooth, sub, up, yawOf } from "../lib/vec";

// Animation states (tools/assets/dn_guest.py DOOR_STATES / GUEST_STATES)
const DOOR = { hidden: 0, manifest: 1, closed: 2, handle: 3, open: 4, held: 5, slam: 6, vanish: 7 };
const GUEST = { hidden: 0, emerge: 1, reach: 2, grab: 3, pull: 4, withdraw: 5, miss: 6 };

// Animation lengths in ticks (DOOR_LEN / GUEST_LEN in dn_guest.py x 20)
const A = { manifest: 24, handle: 28, open: 24, slamShut: 3, vanish: 20, emerge: 52, reach: 24, grab: 12, pull: 32, withdraw: 22 };

// Timeline (ticks).  The script follows the animations exactly; there is no way to read animation progress.
const T_CLOSED = A.manifest;                 // frame assembled, door unfolded from its hinge
const T_HANDLE = T_CLOSED + 6;               // the dread beat: the handle turns by itself
const T_OPEN = T_HANDLE + A.handle;          // latch gives, the door creaks open on the corridor
const T_EMERGE = T_OPEN + 6;                 // something comes up the corridor
const T_HELD = T_OPEN + A.open;
const T_REACH = T_EMERGE + A.emerge;         // arms rise and lengthen
const T_GRAB = T_REACH + A.reach;            // hands close (or close on nothing)
const T_GRIP = T_GRAB + 2;                   // fingers shut at 0.1 s into the grab animation
const T_PULL = T_GRAB + A.grab;              // dragged toward the doorway
const T_WITHDRAW = T_PULL + A.pull;          // lets go, whips back into the dark
const T_SLAM = T_WITHDRAW + 5;
const T_IMPACT = T_SLAM + A.slamShut;        // the leaf hits the frame
const T_GUEST_GONE = T_IMPACT + 8;
const T_VANISH = T_IMPACT + 24;              // the door folds into its keyhole
const T_END = T_VANISH + A.vanish + 4;

/**
 * DN02 - Nightmare Intrusion: The Guest Behind the Door.
 * An antique bedroom door assembles behind the target with no wall to hold it.  Its handle turns,
 * it opens on an impossibly long corridor, and the Guest comes up it.  It grips the frame, leans out,
 * reaches with arms that keep growing, seizes the target (real restraint + squeeze damage), drags it
 * toward the threshold, lets go -- and the door slams shut on the world with a devastating impact.
 */
export default defineSpell("dn02", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center, target } = focus(caster, aim, C.snapRadius);
  const victim: Entity | undefined = target && isAlive(target) ? target : undefined;
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
    if (victim) effect(victim, "slowness", T_REACH - T_HANDLE, C.dreadSlowAmp);
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
  scene.every(7, () => particle(dim, "dn_guest_lamp", L(0, 36, -3)), T_OPEN + 10, T_SLAM);
  scene.at(T_HELD, () => d.state(DOOR.held));

  // -- the Guest comes up the corridor, grips the frame, leans out
  let guest: Actor | undefined;
  scene.at(T_EMERGE, () => {
    guest = scene.spawn("dn_guest", door, { yaw, state: GUEST.emerge });
    sound(dim, "dn_guest_approach", L(0, 30, 10), 1.0);
  });
  scene.at(T_EMERGE + 29, () => { sound(dim, "dn_guest_clicks", L(-20, 50, -4), 1.0); particle(dim, "dn_guest_dust", L(-20, 52, -5)); });
  scene.at(T_EMERGE + 40, () => { sound(dim, "dn_guest_voice", L(-20, 70, -14), 1.0); particle(dim, "dn_guest_breath", L(-24, 70, -22)); });

  // -- reach: the arms rise and keep growing
  scene.at(T_REACH, () => {
    guest?.state(GUEST.reach);
    sound(dim, "dn_guest_voice", L(0, 74, -30), 1.1, 0.9);
    if (victim && isAlive(victim)) effect(victim, "slowness", A.reach + 4, C.reachSlowAmp);
  });
  scene.at(T_REACH + 10, () => sound(dim, "dn_guest_clicks", L(0, 50, -30), 1.0, 1.2));

  // -- grab (or a grasp at nothing)
  let caught = false;
  let release: (() => void) | undefined;
  scene.at(T_GRAB, () => {
    caught = !!victim && isAlive(victim) && distXZ(victim.location, gripAt) <= C.grabRange;
    guest?.state(caught ? GUEST.grab : GUEST.miss);
    if (!caught) {
      sound(dim, "dn_guest_voice", L(0, 60, -40), 0.9, 1.15);
      scene.after(4, () => particle(dim, "dn_guest_breath", L(0, 24, -56)));
    }
  });
  scene.at(T_GRIP, () => {
    if (!caught || !victim || !isAlive(victim)) { caught = false; return; }
    const v = victim;
    const anchor = { x: gripAt.x, y: v.location.y, z: gripAt.z };
    const end = { x: dragEnd.x, y: v.location.y, z: dragEnd.z };
    // real restraint until the slam (released automatically if the scene ends)
    release = restrain(scene, v, T_IMPACT - T_GRIP, anchor);
    // the hands carry it: registered after restrain() so this position wins each tick
    scene.every(1, () => {
      if (!isAlive(v)) return;
      const t = scene.tick;
      const p = t < T_PULL ? 0 : smooth((t - T_PULL) / (A.pull - 1));
      drag(v, lerp(anchor, end, p));
      if (t >= T_PULL && t < T_WITHDRAW && (t - T_PULL) % 3 === 0) particle(dim, "dn_guest_drag", v.location);
    }, T_GRIP, T_IMPACT);
    sound(dim, "dn_guest_grab", v.location, 1.1);
    particle(dim, "dn_guest_grip", up(v.location, 1));
    particle(dim, "dn_guest_squeeze", up(v.location, 1));
    scene.every(C.squeezeEvery, () => {
      if (!isAlive(v)) return;
      damage(v, C.squeezeDamage, caster);
      particle(dim, "dn_guest_squeeze", up(v.location, 1.1));
    }, T_GRIP + 4, T_IMPACT);
  });

  // -- pull toward the threshold
  scene.at(T_PULL, () => {
    guest?.state(GUEST.pull);
    sound(dim, "dn_guest_drag", caught && victim ? victim.location : gripAt, 1.0);
  });

  // -- let go, withdraw, SLAM
  scene.at(T_WITHDRAW, () => {
    guest?.state(GUEST.withdraw);
    sound(dim, "dn_guest_clicks", L(0, 40, -6), 1.0, 1.35);
  });
  scene.at(T_SLAM, () => {
    d.state(DOOR.slam);
    sound(dim, "dn_guest_slam", L(0, 40, -2), 1.8);
  });
  scene.at(T_IMPACT, () => {
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
      const held = caught && victim !== undefined && e.id === victim.id;
      damage(e, C.slamDamage + (held ? C.finisherBonus : 0), caster);
      knockback(e, door, C.slamKnock, C.slamLift);
    }
  });
  scene.at(T_GUEST_GONE, () => { if (guest) scene.despawn(guest); });
  scene.at(T_IMPACT + 6, () => particle(dim, "dn_guest_dust", L(0, 2, -4)));
  scene.at(T_IMPACT + 12, () => particle(dim, "dn_guest_cracklight", L(0, 40, -2)));

  // -- everything folds flat into the keyhole and is gone
  scene.at(T_VANISH, () => {
    d.state(DOOR.vanish);
    sound(dim, "dn_guest_hush", keyhole, 1.0);
  });
  scene.at(T_VANISH + 8, () => particle(dim, "dn_guest_keyhole", keyhole));
  scene.at(T_VANISH + 17, () => particle(dim, "fx_flash", keyhole));
  scene.at(T_VANISH + A.vanish, () => scene.despawn(d));
  scene.endAt(T_END);
});
