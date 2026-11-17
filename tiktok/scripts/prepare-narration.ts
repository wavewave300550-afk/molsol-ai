/**
 * Rebuilds the playback copy (narration.wav) from a narration that is
 * already committed (narration.source.* + alignment.json + narration.json),
 * so CI and new machines render without paying ElevenLabs again.
 * Fails if the committed narration was made for another version of the script.
 *
 * Usage: npm run narration:prepare -- <episode-id>
 */
import { existsSync } from "node:fs";
import { join } from "node:path";
import type { AlignmentFile } from "../src/lib/alignment.ts";
import { approvalStatus, narrationHash } from "./lib/approval.ts";
import { ok, runCli } from "./lib/cli.ts";
import { loadEpisode, readJson } from "./lib/episode-io.ts";
import { prepareNarration, readNarrationMeta } from "./lib/narration.ts";

runCli(async () => {
  const { episode, paths } = loadEpisode(process.argv[2]);
  const meta = readNarrationMeta(paths);
  if (!meta || !existsSync(paths.alignment)) throw new Error(`No committed narration for ${paths.id}.`);
  const source = join(paths.mediaDir, meta.sourceFile);
  if (!existsSync(source)) throw new Error(`The narration audio ${meta.sourceFile} is missing from public/episodes/${paths.id}/.`);
  if (meta.narrationHash !== narrationHash(episode)) {
    throw new Error("The committed narration was made for an earlier version of the script. Generate it again.");
  }
  if (episode.kind === "episode" && meta.source !== "test-audio" && !approvalStatus(episode).approved) {
    throw new Error("The script is not approved (or changed after approval); its narration cannot be used.");
  }
  const alignment = readJson<AlignmentFile>(paths.alignment);
  await prepareNarration({
    episode,
    paths,
    sourceFile: source,
    source: meta.source,
    alignment: alignment.alignment,
    timingSource: alignment.source,
    extra: { voiceId: meta.voiceId, modelId: meta.modelId, requestId: meta.requestId, characterCount: meta.characterCount, recovered: meta.recovered },
  });
  ok(`Narration ready from the committed ${meta.source} take.`);
});
