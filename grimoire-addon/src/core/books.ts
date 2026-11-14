import { Player, Vector3 } from "@minecraft/server";
import { BOOKS, CHARGE_STATE, VISION_STATE } from "../config/books";
import { burst, particle, sound } from "../lib/fx";
import { Actor, Scene, Scenes } from "../lib/scene";
import { add, clamp, lerp, mul, norm, right as rightOf, yawOf } from "../lib/vec";
import { GrimoireDef, SpellMeta } from "./registry";
import { PrepHandle, setPresenter } from "./presentation";

/**
 * Book presentation for the three Grimoires.
 *
 *   select  -> the select sound; the held book flares its built-in circle by itself (crouch, Molang)
 *   prep    -> the charge sounds and the release burst; the held book opens and spins its circle
 *   (BOOKS.vision.entity / BOOKS.charge.entity switch back on the old world-space selection vision,
 *    book_<g>_vision, and charge construct, book_<g>_charge: they never lined up with the
 *    first-person book on an iPhone)
 *   deny    -> a soft negative sound
 *
 * Every visual lives in its own private Scene ("book"), so the entities are removed when the scene
 * ends (or by itself if the player leaves).  At most one vision and one construct exist per player.
 */

const visions = new Map<string, Scene>();
const charges = new Map<string, Scene>();

interface Place { loc: Vector3; yaw: number }

/** A point ahead of the eyes (view clamped vertically), offset to the right and up; faces the player. */
function frame(p: Player, ahead: number, rightOff: number, upOff: number, minY = -1, maxY = 1): Place {
  const head = p.getHeadLocation();
  const raw = p.getViewDirection();
  const d = norm({ x: raw.x, y: clamp(raw.y, minY, maxY), z: raw.z });
  const r = rightOf(d);
  const loc = add(add(add(head, mul(d, ahead)), mul(r, rightOff)), { x: 0, y: upOff, z: 0 });
  return { loc, yaw: yawOf({ x: -d.x, y: 0, z: -d.z }) };
}

function endIn(map: Map<string, Scene>, id: string): void {
  const s = map.get(id);
  map.delete(id);
  if (s && !s.ended) s.end();
}

function track(map: Map<string, Scene>, p: Player, scene: Scene): void {
  map.set(p.id, scene);
  scene.onEnd(() => { if (map.get(p.id) === scene) map.delete(p.id); });
}

function select(p: Player, g: GrimoireDef, meta: SpellMeta): void {
  const pre = BOOKS.prefix[g.id];
  const cfg = BOOKS.vision;
  endIn(visions, p.id);
  if (!cfg.entity) {
    // the held book shows the selection itself (its built-in circle flares on crouch)
    sound(p.dimension, `book_${pre}_select`, p.getHeadLocation(), cfg.volume);
    return;
  }
  const scene = Scenes.start("book", p);
  track(visions, p, scene);
  const f = frame(p, cfg.ahead, cfg.right, cfg.up);
  const vision = scene.spawn(`book_${pre}_vision`, f.loc, { yaw: f.yaw, kind: meta.index, state: VISION_STATE.show });
  sound(p.dimension, `book_${pre}_select`, f.loc, cfg.volume);
  // the vision follows the caster for its short life
  scene.every(1, () => {
    if (!vision.valid) return;
    const n = frame(p, cfg.ahead, cfg.right, cfg.up);
    vision.move(n.loc, n.yaw);
  }, 1);
  scene.endAt(cfg.ticks);
}

function prepStart(p: Player, g: GrimoireDef, meta: SpellMeta): PrepHandle {
  const pre = BOOKS.prefix[g.id];
  const cfg = BOOKS.charge;
  const id = `book_${pre}_charge`;
  endIn(charges, p.id);
  if (!cfg.entity) return prepSound(p, pre);
  const scene = Scenes.start("book", p);
  track(charges, p, scene);

  const where = (): Place => frame(p, cfg.ahead, cfg.right, cfg.up, cfg.minDirY, cfg.maxDirY);
  let place = where();
  let state: number = CHARGE_STATE.form;
  let done = false;
  let lastSeen = 0;
  let retryAt = 0;
  const spawn = (st: number): Actor => scene.spawn(id, place.loc, { yaw: place.yaw, kind: meta.index, state: st });
  let actor = spawn(state);
  sound(p.dimension, `book_${pre}_charge`, place.loc, cfg.soundVolume);

  const finish = (st: number, ticks: number): void => {
    if (done) return;
    done = true;
    actor.state(st);
    scene.endAt(scene.tick + ticks);
  };
  const handle: PrepHandle = {
    tick(held: number) {
      if (done || scene.ended) return;
      lastSeen = scene.tick;
      const target = where();
      place = { loc: lerp(place.loc, target.loc, cfg.follow), yaw: target.yaw };
      const want = held >= cfg.formTicks ? CHARGE_STATE.loop : CHARGE_STATE.form;
      if (!actor.valid) {
        if (scene.tick < retryAt) return;
        // the failsafe lifetime can expire during a very long hold: bring the construct back
        retryAt = scene.tick + 10;
        scene.despawn(actor);
        actor = spawn(want);
        state = want;
      } else if (want !== state) {
        state = want;
        actor.state(state);
      }
      actor.move(place.loc, place.yaw);
      if (held % cfg.moteEvery === 0) particle(p.dimension, `book_${pre}_mote`, place.loc);
      if (held > 0 && held % cfg.soundEvery === 0) sound(p.dimension, `book_${pre}_charge`, place.loc, cfg.soundRepeatVolume);
    },
    release() {
      if (done || scene.ended) return;
      const at = actor.valid ? actor.loc : place.loc;
      burst(p.dimension, `book_${pre}_burst`, at, cfg.burstRadius, cfg.burstCount);
      sound(p.dimension, `book_${pre}_release`, at);
      finish(CHARGE_STATE.release, cfg.releaseTicks);
    },
    cancel() {
      if (done || scene.ended) return;
      finish(CHARGE_STATE.cancel, cfg.cancelTicks);
    },
  };
  // watchdog: if the input system stops ticking this preparation without cancelling it, fold away
  scene.every(1, () => {
    if (!done && scene.tick - lastSeen > cfg.stallTicks) handle.cancel();
  }, 1);
  return handle;
}

/** Preparation without the world construct: the held book opens and spins its own circle; this adds
 *  the charge swell (repeated while held) and, on release, the burst and release sound ahead of it. */
function prepSound(p: Player, pre: string): PrepHandle {
  const cfg = BOOKS.charge;
  let done = false;
  sound(p.dimension, `book_${pre}_charge`, p.getHeadLocation(), cfg.soundVolume);
  return {
    tick(held: number) {
      if (done || !p.isValid) return;
      if (held > 0 && held % cfg.soundEvery === 0) sound(p.dimension, `book_${pre}_charge`, p.getHeadLocation(), cfg.soundRepeatVolume);
    },
    release() {
      if (done || !p.isValid) return;
      done = true;
      const at = frame(p, cfg.ahead, cfg.right, cfg.up, cfg.minDirY, cfg.maxDirY).loc;
      burst(p.dimension, `book_${pre}_burst`, at, cfg.burstRadius, cfg.burstCount);
      sound(p.dimension, `book_${pre}_release`, at);
    },
    cancel() {
      done = true;
    },
  };
}

function deny(p: Player, g: GrimoireDef): void {
  sound(p.dimension, `book_${BOOKS.prefix[g.id]}_deny`, p.getHeadLocation(), BOOKS.deny.volume);
}

/** Selection / preparation presentation for the three Grimoires. */
export function installBooks(): void {
  setPresenter({ select, prepStart, deny });
}
