/**
 * Generates the Thai narration with ElevenLabs, with character timing.
 * Only runs for an approved script, and never twice for the same words
 * (use --force to pay for a new take).
 *
 * Usage: npm run narrate -- <episode-id> [--voice <voice-id>] [--model <model-id>] [--force]
 * Needs ELEVENLABS_API_KEY (see scripts/lib/elevenlabs.ts for where it comes from).
 */
import { writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { TTS } from "../src/lib/config.ts";
import { formatIssues, hasErrors } from "../src/lib/issues.ts";
import { fullNarration, validateEpisode } from "../src/lib/rules.ts";
import { approvalStatus, narrationHash } from "./lib/approval.ts";
import { ok, runCli, step, warn } from "./lib/cli.ts";
import { requireApiKey, synthesizeWithTimestamps } from "./lib/elevenlabs.ts";
import { loadEpisode, publicFileExists } from "./lib/episode-io.ts";
import { prepareNarration, readNarrationMeta } from "./lib/narration.ts";
import { ensureDir } from "./lib/paths.ts";

runCli(async () => {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: { voice: { type: "string" }, model: { type: "string" }, force: { type: "boolean", default: false } },
  });
  const { episode, paths } = loadEpisode(positionals[0]);

  const issues = validateEpisode(episode, { publicFileExists });
  if (hasErrors(issues)) throw new Error(`The script has errors:\n${formatIssues(issues)}`);
  const status = approvalStatus(episode);
  if (!status.approved) {
    throw new Error(`Narration is only generated for an approved script. ${status.reason}\n  Approve it with: npm run approve -- ${episode.id} --by "Name"`);
  }

  // `||` so an empty variable (an unset GitHub Actions variable) falls through.
  const voiceId = values.voice || process.env.ELEVENLABS_VOICE_ID?.trim() || episode.voice?.voiceId || TTS.defaultVoiceId;
  const modelId = values.model ?? episode.voice?.modelId ?? TTS.modelId;
  const existing = readNarrationMeta(paths);
  if (
    !values.force &&
    existing?.source === "elevenlabs" &&
    existing.narrationHash === narrationHash(episode) &&
    existing.voiceId === voiceId &&
    existing.modelId === modelId
  ) {
    ok(`Narration for this exact script, voice and model already exists (${existing.createdAt}). Use --force for a new take.`);
    return;
  }

  const apiKey = requireApiKey();
  if (voiceId === TTS.defaultVoiceId) {
    warn("Using the default voice (George). Choose a voice that sounds natural in Thai: npm run voices");
  }
  const text = fullNarration(episode.scenes);
  step(`Generating narration: ${text.length} characters, model ${modelId}, voice ${voiceId}, language ${TTS.languageCode}`);
  const result = await synthesizeWithTimestamps({
    apiKey,
    voiceId,
    modelId,
    text,
    languageCode: TTS.languageCode,
    voiceSettings: {
      stability: episode.voice?.stability ?? TTS.voiceSettings.stability,
      similarity_boost: episode.voice?.similarityBoost ?? TTS.voiceSettings.similarity_boost,
    },
    outputFormat: TTS.outputFormat,
  });
  ensureDir(paths.mediaDir);
  writeFileSync(paths.narrationSource, result.audio);
  ok(`Saved ${paths.narrationSource} (${(result.audio.length / 1024).toFixed(0)} KB, ${result.characterCount ?? "?"} characters billed)`);
  if (!result.alignment) warn("ElevenLabs returned no character timing; it will be estimated from pauses.");

  await prepareNarration({
    episode,
    paths,
    sourceFile: paths.narrationSource,
    source: "elevenlabs",
    alignment: result.alignment,
    timingSource: "elevenlabs",
    extra: { voiceId, modelId, requestId: result.requestId, characterCount: result.characterCount },
  });
  ok(`Narration ready. Next: npm run render -- ${episode.id}`);
});
