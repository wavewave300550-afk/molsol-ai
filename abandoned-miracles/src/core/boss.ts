/**
 * Boss-facing contracts: what an attack is, what a running attack can do, and
 * the controller every boss implements.
 *
 * The framework owns the things that must be identical for all four bosses
 * (state machine, cancellation, cooldown bookkeeping, damage intake, cleanup).
 * A controller owns everything that makes its boss different: its seven
 * attacks, how it positions, its phase change, its death, its special systems.
 */
import { Entity, Player } from "@minecraft/server";
import { BossKey } from "../config";
import type { Encounter } from "./encounter";
import { StrikeOptions } from "./hazards";
import type { Helper } from "./helpers";
import { Sub } from "./stateMachine";
import { report } from "./trace";
import { TelegraphStyle } from "./visuals";

/** Client animation states driven through the synced `abm:anim` property. */
export const enum AnimState {
  None = 0, // locomotion / idle
  // 1..7 are the seven attacks, by AttackDef.index
  Transition = 8,
  Stagger = 9,
  Death = 10,
  Intro = 11,
}

export interface AttackDef {
  /** Stable id, e.g. "ivory_scythe". */
  id: string;
  /** Display name shown on the HUD while the attack is telegraphed. */
  name: string;
  /** 1..7 - selects the client animation. */
  index: number;
  ultimate?: boolean;
  /** Ticks, or [phase I, phase II]. */
  cooldown: number | [number, number];
  /** False = cannot be cut short by a stagger or by the phase change (default true). */
  interruptible?: boolean;
  /** Tactical weight for the current situation; 0 = not eligible right now. */
  weight(enc: Encounter): number;
  /** Schedule the whole attack on `run`. Must call `run.windows(...)` exactly once. */
  run(run: AttackRun): void;
}

/** One execution of an attack. Everything it schedules dies with its tag. */
export class AttackRun {
  readonly tag: string;
  readonly t0: number;
  readonly target: Player | undefined;
  cancelled = false;
  private declared = false;
  /** Total length in ticks, known after windows(). */
  total = 0;

  constructor(readonly enc: Encounter, readonly def: AttackDef, readonly seq: number) {
    this.tag = `atk${seq}`;
    this.t0 = enc.timeline.now;
    this.target = enc.targeting.primary(this.t0);
  }

  get phase(): 1 | 2 {
    return this.enc.phase;
  }

  get hasWindows(): boolean {
    return this.declared;
  }

  /** Run `fn` `tick` ticks after the attack started (tick 0 runs immediately). */
  at(tick: number, fn: () => void): void {
    if (tick <= 0) {
      try {
        fn();
      } catch (e) {
        report(`attack ${this.def.id}`, e);
      }
      return;
    }
    this.enc.timeline.at(this.t0 + tick, fn, this.tag);
  }

  /**
   * Declare the attack's state windows. The boss is in TELEGRAPH for `telegraph`
   * ticks, ATTACK for `active`, RECOVERY for `recovery`, then returns to IDLE.
   */
  windows(telegraph: number, active: number, recovery: number): void {
    if (this.declared) throw new Error(`${this.def.id}: windows() called twice`);
    this.declared = true;
    this.total = telegraph + active + recovery;
    const now = () => this.enc.timeline.now;
    this.at(telegraph, () => this.enc.sm.setSub(Sub.Attack, now()));
    this.at(telegraph + active, () => this.enc.sm.setSub(Sub.Recovery, now()));
    this.at(this.total, () => this.enc.finishAttack(this));
  }

  /** Telegraph a region at `at - warn` and strike it at `at` (attack-relative ticks). */
  strike(at: number, o: Omit<StrikeOptions, "tag">): void {
    const begin = Math.max(0, at - o.warn);
    this.at(begin, () => this.enc.hazards.strike({ ...o, warn: at - begin, tag: this.tag, label: o.label ?? this.def.id }));
  }

  /** Pick the client animation variant for this run (0..3). */
  variant(n: number): void {
    this.enc.setProp("abm:variant", n);
  }
}

export interface IncomingInfo {
  attacker: Entity | undefined;
  player: Player | undefined;
  projectile: Entity | undefined;
  cause: string;
}

export abstract class BossController {
  abstract readonly key: BossKey;
  abstract readonly displayName: string;
  /** Name of the transformed phase, shown on the HUD during the transition. */
  abstract readonly phase2Name: string;
  abstract readonly trophyItem: string;
  abstract readonly style: TelegraphStyle;
  abstract readonly attacks: readonly AttackDef[];
  readonly experience: number = 500;

  constructor(readonly enc: Encounter) {}

  /** Apply per-phase movement parameters. Called at start and when Phase II begins. */
  abstract configure(phase: 1 | 2): void;

  /** Start the introduction; returns its length in ticks. The boss is protected meanwhile. */
  abstract intro(): number;

  /** Start the phase-change choreography; returns its length in ticks. */
  abstract phaseTransition(): number;

  /** Start the death sequence; returns its length in ticks. */
  abstract death(): number;

  /**
   * Called every tick while the boss is free to move. Steer with enc.loco;
   * return true while walking (POSITIONING) and false while holding (IDLE).
   */
  abstract position(target: Player | undefined): boolean;

  /** Called every tick in every state (special systems: histories, rhythms, trackers). */
  tick(): void {}

  /** Phase II has just become active. */
  phase2Ready(): void {}

  /**
   * Adjust damage about to be dealt to the boss. Runs inside a before-event:
   * it may read the world and change controller state, but anything that
   * changes the world (particles, properties, sounds) must go through enc.defer().
   */
  incoming(damage: number, _info: IncomingInfo): number {
    return damage;
  }

  onHelperGone(_h: Helper): void {}

  /** The current attack was cut short (stagger, phase change, reset, death). */
  onAttackCancelled(_def: AttackDef): void {}

  /** Boss-specific values to persist (e.g. armour states). */
  extra(): Record<string, number> {
    return {};
  }

  restore(_extra: Record<string, number>): void {}

  /** Release everything the controller holds. Called once when the encounter ends. */
  cleanup(): void {}
}

export type ControllerFactory = (enc: Encounter) => BossController;

/** The optional demonstration arena that ships with a boss. */
export interface ArenaInfo {
  /** Structure identifier, e.g. "abm:hall_of_endless_succession". */
  structure: string;
  /** Footprint (blocks per side) and height of the structure. */
  size: number;
  height: number;
  /** Lang key of the arena's name. */
  nameKey: string;
}

/** What a boss module exports to the registry. */
export interface BossModule {
  create: ControllerFactory;
  arena: ArenaInfo;
  /** Entity identifiers of this boss's helper entities. */
  helpers: readonly string[];
}
