# The Abandoned Miracles

*Four perfect miracles. Four catastrophic successes.*

A Minecraft Bedrock Edition boss add-on (work in progress — see [PROGRESS.md](PROGRESS.md)).

* Importable add-on: [`dist/The_Abandoned_Miracles.mcaddon`](dist/The_Abandoned_Miracles.mcaddon)
* Target: Bedrock **1.26.60** or newer, stable Script API only (`@minecraft/server` 2.11.0, `@minecraft/server-ui` 2.3.0). No experimental toggles.

```
npm install          # typings, esbuild, TypeScript
npm run build        # generate packs + dist/*.mcaddon
npm run validate     # static validation (add -- --mct for Mojang's validator)
npm run sim          # headless encounter simulation
```

Full documentation is written at the end of production.
