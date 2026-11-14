# Real-server probe

A small behaviour pack that drives the add-on inside a real Bedrock Dedicated Server, so the script
side is tested by the game engine instead of the mock.

It spawns a simulated player (`@minecraft/server-gametest`), puts a Grimoire in its hand, selects a
spell by crouching, holds Use and releases it - the same input path a person uses - and logs every
spell entity (position, facing, state, kind, size) each tick to the server log.

Requirements: a Bedrock Dedicated Server whose world has the **Beta APIs** experiment on (the
gametest module is beta), `@minecraft/server-gametest` allowed in `config/default/permissions.json`,
and both packs in the world's `world_behavior_packs.json`. Running the server means accepting the
Minecraft EULA; that is the server owner's decision.

Server console:

```
tickingarea add circle 0 0 0 4 probe
scriptevent probe:terrain            # optional: height map around the test site
scriptevent probe:run all            # or: probe:run dn02,ed01      with six husks as targets
scriptevent probe:run all solo       # no targets
```

Then turn the log into scene traces and look at them:

```
python3 tools/real_trace.py <server log>          # writes tests/.out/trace/<id>_real.json and a summary
python3 tools/scene.py dn02 --real --view wide
```

What the server cannot show is anything the client draws: models, textures, the held book.
