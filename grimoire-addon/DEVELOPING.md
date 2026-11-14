# Developing Grimoire: Rebirth of the Arcane

Minecraft **Bedrock** add-on (stable 26.6x, `min_engine_version` 1.26.60, `@minecraft/server` 2.11.0).
3 Grimoires, 18 spells. Everything is generated from source: Python builds models, textures,
animations, particles and sounds; TypeScript holds the gameplay.

```
tools/kit/        asset toolkit (geo, tex, anim, parts, particles, synth, glyphs, pack, render)
tools/assets/     one module per asset family; each has build(pack)        -> packs
src/core/         registry (approved cooldowns), input state machine, HUD, persistent state
src/lib/          scene, targeting, combat, tempblocks, fx, vec
src/config/       tunable gameplay values, one file per spell
src/spells/       one file per spell (dw01..dw06, dn01..dn06, ed01..ed06)
tests/            strict Script-API mock + headless tests
behavior_packs/grimoire_bp, resource_packs/grimoire_rp     generated output (committed)
```

Reference slice to imitate: `tools/assets/dw_seraph.py`, `tools/assets/dw_common.py`,
`src/config/dw01.ts`, `src/spells/dw01_seraphic_litany.ts`.

## 1. Rules that never bend

* Exactly three book items; spells are never items. No mana / MP / stamina / HP cost / ammo /
  durability. Each spell has only its own cooldown (`src/core/registry.ts`, do not edit).
* Controls are fixed (crouch = next spell, hold Use = prepare, release = cast). Spells never read input.
* No custom cameras, no forced camera moves, no global game-rule changes, no player.json overrides,
  no experimental toggles, no custom materials. Stable APIs only.
* Nothing permanent: every entity, effect and block a spell creates goes through its `Scene`
  and is gone when the scene ends. Never break or replace existing blocks; temporary blocks are
  placed only into air via `blocksFor(scene)`.
* The central thing in every spell is an **original animated 3D model**, never a particle cloud,
  a vanilla mob, or a recolour of another model. Particles and sound support the model.
* Gameplay must be real and must line up with the visuals (damage lands when the animation hits,
  walls actually block, heals actually heal, restraint actually holds).
* The brief is a foundation, not a ceiling: add secondary motion, staged manifestation,
  distinctive departures and original detail wherever it makes the spell better.

## 2. Visual languages (do not mix)

| Grimoire | Palette | Language |
|---|---|---|
| Divine Word (`dw_`) | ivory `#f5f0e1`, antique gold `#c9a24a`, white-gold `#fff3c4`, pale silver `#d8dde3`, royal blue accent `#2b3f8f` | living inscriptions (`glyphs.FIRST_WORD`), words becoming architecture, celestial constructs, solemn and ceremonial |
| Dream & Nightmare (`dn_`) | dream: ivory, peach `#ffd9b8`, dusty pink `#e8b4c8`, soft gold `#e9cf8a`, pale blue `#bcd6f0`; nightmare: midnight indigo `#2a2d52`, bruised mauve `#6a4a6e`, faded burgundy `#6e2f3a`, aged ivory `#cfc6b0`, cold gray `#8b8f9a` | impossible rooms, doors, stairs, windows, porcelain, fabric, living furniture; beauty that warps. No angels, no scripture, not plain "shadow magic" |
| Elemental Dragon (`ed_`) | antique bronze `#8a6a3a`, bone ivory `#e9dfc6`, moss, basalt, ember orange, sapphire, ice white, silver-blue | prehistoric anatomy, fossils, geology, botany, heat shimmer, water, feathers (`glyphs.DRACONIC`) |

## 3. Asset kit (Python)

### Space, units, scale
* Author in **bb space**: right-handed, `+X` = east = the model's **right-hand side**, `+Y` up,
  `+Z` south. **A model's front faces -Z.** Units are 1/16 block. Rotations are degrees,
  right-handed, applied X then Y then Z; a bone's animation rotation is added to its bind rotation.
  Positive `rx` tips +Y toward +Z (backward), positive `ry` swings +Z toward +X, positive `rz`
  swings +X toward +Y. The exporter converts to Bedrock's conventions; never hand-flip anything.
* Giant things: model at a comfortable size and pass `scale=` to `pack.actor` (the Seraphim is
  modelled ~110 units tall and rendered at `scale=2.0` -> 14 blocks). `density` (texture pixels per
  unit) may be < 1 on huge parts.
* The entity origin (0,0,0) is where scripts teleport it. Put feet/ground contact at y = 0
  for grounded things.

### Model / Bone / Cube (`kit.geo`)
```python
m = Model("name", density=1.0, bounds=(width_blocks, height_blocks, (ox, oy, oz)), alts=("skin2",))
b = m.bone("body", parent=None|"root"|bone, pivot=(x, y, z), rot=(rx, ry, rz))
b.cube(origin_min_corner, size, mat, rot=None, pivot=None, inflate=0, density=None, variant=0,
       faces=None, mats={"north": other_mat})
b.box(center, size, mat, ...)                # cube by centre
b.plane("x"|"y"|"z", center, w, h, mat, ...) # zero-thickness sheet: ONE image, seen mirrored from behind
b.locator("name", (x, y, z))                 # anchor for animation particles
ring(bone, center, radius, n, (tangent, radial, thick), mat, axis="y"|"x"|"z")
```
`bounds` is the culling box in blocks **after scaling is NOT applied** - give generous numbers for
big or far-moving models (they vanish when the box leaves the screen). Each bone must use only
solid materials or only `mode="blend"` materials (blend bones render with `entity_alphablend`).
`variant` asks for a different random tile of the same material so repeats are not identical.
Faces sharing material + pixel size + variant share texture space, so repeated parts are cheap.

### Materials (`kit.tex`) - all return a `Mat`
`flat, speck, vgrad, sgrad (spatial gradient along a model axis), mottled, scales, plates, marble,
metal, stone, bone_mat, wood, porcelain, fabric, foliage (cut-out), crystal (blend), fluid (blend),
glow_flat, feather (cut-out plane, quill at top), eye_mat, windowed, shaped(mask, ...) with masks
m_disc/m_ring/m_diamond/m_star/m_crescent/m_leaf, bitmap_cut(rows, ...), inscription, glyph_rows,
magic_circle, and the wrappers trimmed(), banded(), stamped(), overlay(), alt()`.
Tiles are `(h, w, 5)` floats: r, g, b, alpha (cut-out < 0.5, or opacity in blend mode), **glow**
(0..1 self-illumination; use it generously on magical parts - glow reads in the dark).
Write your own painter when needed: `Mat(fn, key, mode="solid"|"blend", spatial=False, directional=False)`
with `fn(ctx)` using `ctx.w, ctx.h, ctx.U, ctx.V, ctx.X/Y/Z, ctx.rng, ctx.variant, ctx.alt, ctx.face`.
Keep keys unique per parameter set. **Texture skins**: `Model(alts=("x",))` + `tex.alt(base, x=other)`
paints a second atlas with the same layout; scripts switch it with `actor.skin(1)`.
Other variation tools: `pack.actor(kinds=[model2, ...])` (whole different geometry, `actor.kind(n)`)
and `size_prop=True` (`actor.size(f)` multiplies rendered scale).

### Animation (`kit.anim`, `kit.parts`)
```python
a = Anim("walk", length=2.0, loop=True|False|"hold")
a.rot("bone", (x, y, z))                       # numbers or expressions
a.rot("bone", {0: (0,0,0), 0.5: (20,0,0)})     # keyframes (smooth catmull-rom by default)
a.pos(...); a.scl("bone", 1.2 | (x,y,z) | {t: v})
a.sound(t, "short_name"); a.particle(t, "short_name", locator="name")
S(amp, period, phase=0, base=0)   # sine on q.anim_time (loops must have length = k * period)
LIFE(amp, period, phase, base)    # sine on q.life_time (never pops; best for idles)
M("molang", py_fn)                # raw Molang with a python twin for previews
sym(a, "wing_{s}_a1", rot=...)    # right side as given, left side mirrored ({s} -> r / l)
wave(a, [bones], axis, amp, period, lag)   # travelling wave down a chain (tails, necks, ribbons)
flutter(a, [bones]); feather_wing(...); segmented(...)
```
Name right-side bones `*_r` (at +X) and left `*_l`. Use many bones where anatomy bends: spines,
necks and tails are chains of 4-8 bones. Give every creature weight (anticipation, overshoot,
settling), breathing, and secondary motion. Budget: <= ~450 cubes, <= ~160 bones, <= ~60
Molang-driven bones per model, texture <= 512x512 (1024 only for the largest hero models).

### Entities (`pack.actor`)
```python
pack.actor("dw_thing", model, anims, states={0: ["hidden"], 1: ["arrive"], 2: ["idle", "flap"]},
           always=["breathe"], scale=1.0, lifetime=120, kinds=None, size_prop=False,
           visibility=[{"bone*": "q.property('grimoire:state') >= 2"}],
           sounds={"roar": "grimoire.ed_roar"}, particles={"dust": "grimoire:fx_dust"},
           display="Name", blend=0.2)
```
Creates the behaviour entity (no AI, no gravity, invulnerable, transient, self-despawning after
`lifetime` seconds as a failsafe), client entity, render controller, animations and an animation
controller that mirrors the int property `grimoire:state`. **State 0 must be a hidden pose**
(`hidden.scl("root", 0.0)`); scripts set the real state in the same tick they spawn. One-shot
state animations use `loop="hold"`. Document your state numbers in a `STATES` dict and mirror it
as a const in the spell file. `lifetime` must exceed the longest spell that uses the actor.

Three things the real engine taught us (see `tests/probe`):

* **Properties arrive one tick late.** A property set in the tick an entity spawns is still at its
  default in that tick; that is why state 0 must be hidden.
* **Facing is not the entity rotation.** A model is drawn turned by the mob's body yaw, which the
  game steers itself (it trails a turn in place by up to 75 degrees). Every actor therefore has the
  synced property `grimoire:yaw` and a wrapper bone `gface` that turns the model by
  `q.property('grimoire:yaw') - q.body_y_rotation`. Turn actors only through `Actor.move` /
  `Actor.face` / `spawn({ yaw })`, which keep the property in step; never call `setRotation`.
* **Textures are 32-bit TGA** (`Model.save`), as for every vanilla texture drawn with an emissive
  material. Alpha is glow (255 = lit normally, 5 = full glow); alpha 0 is cut-out and must be black.

### Particles (`kit.particles`, via `particles(pack)` from `assets.a_fx_common`)
`fx.effect("dn_petals", "petal", count=8, life=(1, 2), size=(0.2, 0.05), shape=("sphere", 1.5),
speed=(0.3, 1), accel=(0, -1, 0), drag=1, colors=["#rrggbbaa", ...], blend="add"|"blend"|"alpha",
spin=(360, 90), facing="lookat_xyz"|"emitter_transform_xz"|"lookat_y", sprites=[...])`.
Sprites: dot glow hard spark star ring ringthin diamond shard ember petal feather leaf moon drop
flake puff smoke slash beam wave arc cross eye scale bone rock note door key window glyph1-8 rune1-6.
Scripts are budgeted (90 particles/tick world-wide): prefer a few well-shaped bursts.

### Sound (`kit.synth as sy`) - original synthesis only
`choir, bell, pluck, pad, roar, wind, whoosh, thump, crack, rumble, creak, water, heartbeat,
shimmer, scribble, osc, noise, sweep, formants, lowpass/highpass/bandpass, reverb, at(...),
mixdown, pitch`; then `sy.save(pack, "ed_stomp", sig, volume=1, max_distance=48, variants=[...])`
registers `grimoire.ed_stomp`. Never imitate a recognisable melody. Keep clips <= ~3 s
(ultimates may have a few 4-6 s beds). Every creature gets its own voice.

### Build, preview, look at your work
```
python3 tools/build.py --only <module>[,<module>] --preview     # writes tools/_preview/*.png
```
Call `pack.preview("name", model, [pose, ...], views=((yaw, pitch), ...), skin="alt")` in your
module where a pose is `None`, `(anim, t)` or `[(anim, t), (anim2, t2)]` (combined). **Open the PNGs
and judge them** - silhouette first, then detail. Iterate until the model is unmistakably what
the brief describes. Previews show bb space exactly as the game will render it.

## 4. Gameplay framework (TypeScript)

```ts
export default defineSpell("dn02", ({ caster, scene, aim, heldTicks }) => { ... return false to refuse ... });
```
* `scene.at(tick, fn)`, `scene.after(delay, fn)`, `scene.every(n, fn(elapsed), from, to)`,
  `scene.span(from, to, fn(progress01))`, `scene.endAt(tick)` (**always schedule the end**),
  `scene.onEnd(fn)`, `scene.tick`, `scene.dim`, `scene.origin`. 20 ticks = 1 s, `secs(1.5)`.
* `const a = scene.spawn("dn_guest", loc, { yaw, state, kind, size, skin })` -> `Actor` with
  `.state(n) .kind(n) .size(f) .skin(n) .move(loc, yaw?) .face(yaw) .loc .valid`; `scene.despawn(a)`;
  `scene.follow(actor, entity, dy)`. Moving an actor = call `.move()` every tick along a path
  (`lerp`, `bezier`, `spline`, `polar` from `lib/vec`). Yaw: `yawOf(direction)`; the model's front
  points along its yaw.
* Targeting: `focus(caster, aim, snap)` -> `{center, target?}`; `hostiles(dim, center, radius, caster, max?)`;
  `allies(dim, center, radius, caster)`; `groundBelow(dim, loc)`; `isAlive(e)`; `aim.point/ground/forward/yaw/entity`.
  Always re-query hostiles when a hit lands; entities die and move.
* Combat: `damage(e, n, caster)`, `knockback(e, from, h, v)`, `shove(e, dir, h, v)`, `heal(e, n)`,
  `effect(e, "slowness", ticks, amp)`, `restrain(scene, e, ticks, anchor?)`, `drag(e, to)`,
  `addWard({scene, protects, factor, pool?, onAbsorb?, onBreak?})` (true damage mitigation),
  `dissolveProjectiles(scene, center, radius)`.
* Temporary blocks: `const tb = blocksFor(scene); tb.place(loc, BARRIER|LIGHT); tb.column(x, y, z, h);
  tb.remove(loc)`. Barriers give real collision and pathfinding; never leave a player sealed in
  (keep doorways; barriers refuse to spawn inside players).
* FX: `particle(dim, "dn_petals", loc)`, `ring`, `line`, `burst`, `sound(dim, "dn_door_slam", loc, vol, pitch)`.
* Put every number that affects balance in `src/config/<id>.ts` with a comment.
* If no enemy is present the spell must still perform (aimed at `focus().center`).
* Telegraph dangerous areas with `scene.spawn("telegraph", loc, {kind: 0 dw | 1 dn | 2 ed, size: radius, state: 1})`
  (state 1 fills in 1 s, 4 fills in 2 s, 2 holds, 3 flashes out).

### Look at a whole spell (`tools/scene.py`)
Model previews show one model; they do not show whether a spell puts it in the right place.  The
scene previewer replays a recorded cast with the real models, poses, sizes and facings:
```
GRIMOIRE_SCENE=1 python3 tools/build.py            # once: also writes tools/_scene/*.pkl (needs cloudpickle)
node tests/run.mjs trace [dw01,ed03]               # record casts on the flat test world
TERRAIN=hills node tests/run.mjs trace             # ... and on rolling ground with a ledge
python3 tools/scene.py ed01 --view wide --n 6      # contact sheet in tools/_preview/scene/
python3 tools/scene.py ed01 --hills --report       # table: when each actor lives, how high above the ground
```
Views: `chase`, `wide`, `pov`, `top`, `side`, `front`, or `--cam r,u,f,r,u,f` (eye and target relative to
the caster).  The blue box is the caster, green boxes are enemies, rings are particles.  **Check new
spells on the hills terrain**: anything that should stand on the ground must follow it (add its
actor to `src/config/ground.ts`).

### Run it in the real server (`tests/probe`)
`tests/probe/README.md` describes a harness pack that makes a simulated player cast spells through
the real input path on a Bedrock Dedicated Server and logs every spell entity;
`tools/real_trace.py` turns the server log into traces for `tools/scene.py --real`.

## 5. Tests
```
npx tsc --noEmit -p tsconfig.json                  # type check (must be clean for your files)
node tests/run.mjs spells dn02                     # full-cast / no-target / caster-leaves tests
node tests/run.mjs controls                        # input + cooldown rules
```
The mock is strict: unknown entity / particle / sound ids, undefined properties, out-of-range
states, NaN positions, leftover entities or blocks, and any `[grimoire]` warning fail the test.
If a parallel build made your freshly built ids look "unknown", rebuild your module and rerun.

## 6. File ownership when several people work at once
Own only your slice: `tools/assets/<your prefix>*.py`, `src/config/<your ids>.ts`,
`src/spells/<your ids>_*.ts` (+ optional `src/spells/_<slice>_helpers.ts`). Treat `tools/kit/`,
`src/core/`, `src/lib/`, `tests/`, other slices and the shared actors (`seraph`, `telegraph`,
`dw_circle`, `dw_column`, `dw_mark`) as read-only; use them freely but report needed changes
instead of editing. Never run a full `tools/build.py` without `--only` while others are working.
