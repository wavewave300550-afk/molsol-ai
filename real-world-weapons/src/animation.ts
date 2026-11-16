import { Player, PlayAnimationOptions, system, world } from "@minecraft/server";
import { heldWeapon, WeaponType } from "./weapons.js";

/**
 * Drives the player-side weapon animations.
 *
 * Bedrock only lets add-ons animate the player's own bones from the client entity
 * (player.entity.json).  Overriding that file breaks every other add-on that does the
 * same, so instead the two looping animations of the held weapon are started with
 * Entity.playAnimation in dedicated runtime controllers:
 *   animation.rww.<weapon>.arms  (override: arms + item, all locomotion states, attacks)
 *   animation.rww.<weapon>.body  (additive: torso twist, lunges and steps)
 * Everything frame-dependent (walking, jumping, attack timing via variable.attack_time,
 * combo selection, equip intro) is evaluated client-side in Molang, so only equip
 * changes need network traffic.  The animations stop themselves (stop expression)
 * when the weapon leaves the main hand.
 *
 * Runtime controllers live on the client copy of the entity, so they are re-sent when
 * a player joins, respawns, changes dimension, or comes back into range of a viewer.
 */
export const ARMS_CONTROLLER = "controller.animation.rww.arms";
export const BODY_CONTROLLER = "controller.animation.rww.body";

export function stopExpression(weapon: WeaponType): string {
  return `!q.equipped_item_any_tag('slot.weapon.mainhand', 'rww:${weapon}') || q.is_sleeping || q.is_emoting`;
}

interface HolderState {
  weapon?: WeaponType;
  suppressed: boolean;
  /** viewers that received the current animation while in range */
  near: Set<string>;
}

const NEAR = 48;
const FAR = 64;

export class AnimationDriver {
  private readonly states = new Map<string, HolderState>();
  /** callbacks fired when a player draws a weapon (used by combat rules) */
  onEquip?: (player: Player, weapon: WeaponType) => void;

  private state(player: Player): HolderState {
    let s = this.states.get(player.id);
    if (!s) {
      s = { suppressed: false, near: new Set() };
      this.states.set(player.id, s);
    }
    return s;
  }

  play(holder: Player, weapon: WeaponType, viewers?: Player[]): void {
    if (!holder.isValid) return;
    const base: PlayAnimationOptions = { stopExpression: stopExpression(weapon), blendOutTime: 0.25 };
    if (viewers) base.players = viewers.filter((v) => v.isValid);
    if (viewers && base.players!.length === 0) return;
    try {
      holder.playAnimation(`animation.rww.${weapon}.arms`, { ...base, controller: ARMS_CONTROLLER });
      holder.playAnimation(`animation.rww.${weapon}.body`, { ...base, controller: BODY_CONTROLLER });
    } catch {
      // the entity may have been unloaded between the check and the call
    }
  }

  /** Re-send to every player that should see `holder` (used after equip / respawn / dimension change). */
  broadcast(holder: Player): void {
    const s = this.state(holder);
    if (!s.weapon || s.suppressed) return;
    this.play(holder, s.weapon);
    s.near = new Set(this.viewersInRange(holder, NEAR).map((p) => p.id));
  }

  private viewersInRange(holder: Player, range: number): Player[] {
    const out: Player[] = [];
    for (const p of world.getAllPlayers()) {
      if (p.id === holder.id || p.dimension.id !== holder.dimension.id) continue;
      const dx = p.location.x - holder.location.x;
      const dz = p.location.z - holder.location.z;
      if (dx * dx + dz * dz <= range * range) out.push(p);
    }
    return out;
  }

  /** Poll the held items (every 2 ticks). */
  update(): void {
    for (const player of world.getAllPlayers()) {
      const s = this.state(player);
      const weapon = heldWeapon(player)?.type;
      const suppressed = player.isSleeping || player.isEmoting;
      if (weapon !== s.weapon) {
        s.weapon = weapon;
        s.suppressed = suppressed;
        if (weapon) {
          this.onEquip?.(player, weapon);
          // two ticks later, so clients have the new held item before the animation arrives
          system.runTimeout(() => {
            if (player.isValid && heldWeapon(player)?.type === weapon) this.broadcast(player);
          }, 2);
        }
        continue;
      }
      if (s.suppressed !== suppressed) {
        s.suppressed = suppressed;
        if (!suppressed && weapon) this.broadcast(player);
      }
    }
  }

  /** Re-send to viewers that come back into range (their client may have dropped the entity). */
  updateVisibility(): void {
    for (const holder of world.getAllPlayers()) {
      const s = this.states.get(holder.id);
      if (!s?.weapon || s.suppressed) continue;
      const fresh: Player[] = [];
      const inRange = new Set<string>();
      for (const v of this.viewersInRange(holder, FAR)) {
        const dx = v.location.x - holder.location.x;
        const dz = v.location.z - holder.location.z;
        const d2 = dx * dx + dz * dz;
        if (d2 <= NEAR * NEAR) {
          inRange.add(v.id);
          if (!s.near.has(v.id)) fresh.push(v);
        } else if (s.near.has(v.id)) {
          inRange.add(v.id); // hysteresis band: keep
        }
      }
      s.near = inRange;
      if (fresh.length) this.play(holder, s.weapon, fresh);
    }
  }

  onSpawn(player: Player, initialSpawn: boolean): void {
    const s = this.state(player);
    s.near.clear();
    if (initialSpawn) {
      // show everyone's current weapon pose to the new player
      for (const holder of world.getAllPlayers()) {
        const hs = this.states.get(holder.id);
        if (holder.id !== player.id && hs?.weapon && !hs.suppressed && holder.dimension.id === player.dimension.id) {
          this.play(holder, hs.weapon, [player]);
          hs.near.add(player.id);
        }
      }
    }
    if (s.weapon) system.runTimeout(() => player.isValid && this.broadcast(player), 2);
  }

  onDimensionChange(player: Player): void {
    for (const hs of this.states.values()) hs.near.delete(player.id);
    this.onSpawn(player, true);
  }

  onLeave(playerId: string): void {
    this.states.delete(playerId);
    for (const hs of this.states.values()) hs.near.delete(playerId);
  }

  weaponOf(player: Player): WeaponType | undefined {
    return this.states.get(player.id)?.weapon;
  }
}
