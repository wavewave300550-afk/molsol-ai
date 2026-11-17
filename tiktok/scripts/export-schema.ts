/**
 * Writes episodes/episode.schema.json from the zod schema so editors can
 * autocomplete and check episode.json files ("$schema": "../episode.schema.json").
 *
 * Usage: npm run schema
 */
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";
import { EpisodeSchema } from "../src/lib/schema.ts";
import { ok, runCli } from "./lib/cli.ts";
import { projectRoot } from "./lib/paths.ts";

runCli(() => {
  const schema = z.toJSONSchema(EpisodeSchema, { io: "input", unrepresentable: "any" });
  writeFileSync(join(projectRoot, "episodes", "episode.schema.json"), `${JSON.stringify(schema, null, 2)}\n`);
  ok("Wrote episodes/episode.schema.json");
});
