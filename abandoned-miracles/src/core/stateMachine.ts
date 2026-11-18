/**
 * BossStateMachine - the explicit combat state model.
 *
 *   INTRO -> PHASE_1 -> PHASE_TRANSITION -> PHASE_2 -> DEATH
 *
 * Exactly two combat phases exist (PHASE_1 and PHASE_2). The substates below
 * describe what the boss is doing inside a phase; they are not extra phases.
 * Illegal transitions are refused and reported, so overlapping attacks or a
 * death during a transition cannot leave the fight in an impossible state.
 */
import { report, trace } from "./trace";

export enum Top {
  Intro = "INTRO",
  Phase1 = "PHASE_1",
  Transition = "PHASE_TRANSITION",
  Phase2 = "PHASE_2",
  Death = "DEATH",
}

export enum Sub {
  Idle = "IDLE",
  Positioning = "POSITIONING",
  Telegraph = "TELEGRAPH",
  Attack = "ATTACK",
  Recovery = "RECOVERY",
  Stagger = "STAGGER",
  Reset = "RESET",
}

const TOP_EDGES: Record<Top, Top[]> = {
  [Top.Intro]: [Top.Phase1, Top.Phase2, Top.Death],
  [Top.Phase1]: [Top.Transition, Top.Death],
  [Top.Transition]: [Top.Phase2, Top.Death],
  [Top.Phase2]: [Top.Death],
  [Top.Death]: [],
};

const SUB_EDGES: Record<Sub, Sub[]> = {
  [Sub.Idle]: [Sub.Positioning, Sub.Telegraph, Sub.Stagger, Sub.Reset],
  [Sub.Positioning]: [Sub.Idle, Sub.Telegraph, Sub.Stagger, Sub.Reset],
  [Sub.Telegraph]: [Sub.Attack, Sub.Recovery, Sub.Idle, Sub.Stagger, Sub.Reset],
  [Sub.Attack]: [Sub.Recovery, Sub.Idle, Sub.Stagger, Sub.Reset],
  [Sub.Recovery]: [Sub.Idle, Sub.Stagger, Sub.Reset],
  [Sub.Stagger]: [Sub.Idle, Sub.Reset],
  [Sub.Reset]: [Sub.Idle],
};

export class BossStateMachine {
  top: Top = Top.Intro;
  sub: Sub = Sub.Idle;
  topSince = 0;
  subSince = 0;
  /** Ordered record of top-level states visited (asserted on by tests). */
  readonly history: Top[] = [Top.Intro];

  constructor(private readonly label: string) {}

  get inCombat(): boolean {
    return this.top === Top.Phase1 || this.top === Top.Phase2;
  }

  /** Busy executing an attack (cannot start another). */
  get busy(): boolean {
    return this.sub === Sub.Telegraph || this.sub === Sub.Attack || this.sub === Sub.Recovery;
  }

  setTop(next: Top, now: number): boolean {
    if (next === this.top) return true;
    if (!TOP_EDGES[this.top].includes(next)) {
      report("state machine", new Error(`${this.label}: illegal ${this.top} -> ${next}`));
      return false;
    }
    trace("top", { boss: this.label, from: this.top, to: next, tick: now });
    this.top = next;
    this.topSince = now;
    this.history.push(next);
    // every top-level change starts from a clean substate
    this.sub = Sub.Idle;
    this.subSince = now;
    return true;
  }

  setSub(next: Sub, now: number): boolean {
    if (next === this.sub) return true;
    if (!SUB_EDGES[this.sub].includes(next)) {
      report("state machine", new Error(`${this.label}: illegal substate ${this.sub} -> ${next}`));
      return false;
    }
    this.sub = next;
    this.subSince = now;
    return true;
  }

  /** Restore after a world reload: adopt a phase without replaying the intro. */
  restore(phase: 1 | 2, now: number): void {
    this.top = phase === 2 ? Top.Phase2 : Top.Phase1;
    this.sub = Sub.Idle;
    this.topSince = this.subSince = now;
    this.history.push(this.top);
  }
}
