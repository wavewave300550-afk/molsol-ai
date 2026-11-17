/**
 * Generates the Thai narration with ElevenLabs, with character timing, in the
 * channel narrator's voice (Madame Scientia) unless another voice is chosen.
 * Only runs for an approved script, and never twice for the same words
 * (use --force to pay for a new take).
 *
 * The take is saved the moment it arrives, before mastering: the MP3 as
 * narration.source.mp3 and ElevenLabs' timing and request details as
 * elevenlabs-take.json. If anything after that fails, running this again
 * reuses the saved take instead of sending a new request.
 *
 * Usage: npm run narrate -- <episode-id> [--dry-run] [--voice <voice-id>] [--model <model-id>] [--force]
 *   --dry-run  show exactly what would be sent (voice, model, URL, characters)
 *              without sending anything: no key needed, no credits used.
 * Needs ELEVENLABS_API_KEY (see scripts/lib/elevenlabs.ts for where it comes from).
 */
import { writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { TTS } from "../src/lib/config.ts";
import { formatIssues, hasErrors } from "../src/lib/issues.ts";
import { fullNarration, validateEpisode } from "../src/lib/rules.ts";
import { approvalStatus, narrationHash } from "./lib/approval.ts";
import { ok, runCli, step, warn } from "./lib/cli.ts";
import { buildTtsRequest, requireApiKey, synthesizeWithTimestamps } from "./lib/elevenlabs.ts";
import { loadEpisode, publicFileExists } from "./lib/episode-io.ts";
import { prepareNarration, readNarrationMeta } from "./lib/narration.ts";
import { ensureDir } from "./lib/paths.ts";
import { findReusableTake, saveTake } from "./lib/take.ts";
import { describeVoice, resolveVoice } from "./lib/voice.ts";

runCli(async () => {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      voice: { type: "string" },
      model: { type: "string" },
      force: { type: "boolean", default: false },
      "dry-run": { type: "boolean", default: false },
    },
  });
  const { episode, paths } = loadEpisode(positionals[0]);
  const issues = validateEpisode(episode, { publicFileExists });
  const status = approvalStatus(episode);
  const voice = resolveVoice({ option: values.voice, env: process.env.ELEVENLABS_VOICE_ID, episode: episode.voice?.voiceId });
  const modelId = values.model?.trim() || episode.voice?.modelId || TTS.modelId;
  const voiceSettings = {
    stability: episode.voice?.stability ?? TTS.voiceSettings.stability,
    similarity_boost: episode.voice?.similarityBoost ?? TTS.voiceSettings.similarity_boost,
  };
  const text = fullNarration(episode.scenes);
  const request = { voiceId: voice.voiceId, modelId, text, languageCode: TTS.languageCode, voiceSettings, outputFormat: TTS.outputFormat };

  if (values["dry-run"]) {
    const { url } = buildTtsRequest({ ...request, apiKey: "(not sent)" });
    const scriptState = hasErrors(issues)
      ? "has errors, so a real run would stop (npm run validate)"
      : status.approved
        ? `approved by ${episode.approval?.approvedBy}`
        : `not approved, so a real run would stop here: ${status.reason}`;
    console.log(`Narration plan for ${episode.id} (dry run: nothing is sent, no credits are used)`);
    console.log(`  Voice:    ${describeVoice(voice)}, from ${voice.source}`);
    console.log(`  Model:    ${modelId}, language ${TTS.languageCode}, stability ${voiceSettings.stability}, similarity ${voiceSettings.similarity_boost}, no speed setting`);
    console.log(`  Request:  POST ${url}`);
    console.log(`  Text:     ${text.length} characters (ElevenLabs bills by character)`);
    console.log(`  Script:   ${scriptState}`);
    console.log(`  API key:  ELEVENLABS_API_KEY is ${process.env.ELEVENLABS_API_KEY?.trim() ? "set here (value hidden)" : "not set here"}`);
    return;
  }

  if (hasErrors(issues)) throw new Error(`The script has errors:\n${formatIssues(issues)}`);
  if (!status.approved) {
    throw new Error(`Narration is only generated for an approved script. ${status.reason}\n  Approve it with: npm run approve -- ${episode.id} --by "Name"`);
  }
  const hash = narrationHash(episode);
  const existing = readNarrationMeta(paths);
  if (
    !values.force &&
    existing?.source === "elevenlabs" &&
    existing.narrationHash === hash &&
    existing.voiceId === voice.voiceId &&
    existing.modelId === modelId
  ) {
    ok(`Narration for this exact script, voice and model already exists (${existing.createdAt}). Use --force for a new take.`);
    return;
  }

  // A take an earlier run paid for but never finished preparing (for example, mastering failed).
  const saved = values.force ? null : findReusableTake(paths, { narrationHash: hash, voiceId: voice.voiceId, modelId });
  if (saved) {
    ok(`Using the ElevenLabs take saved on ${saved.createdAt} for this exact script, voice and model: no request, no credits. Use --force for a new take.`);
    await prepareNarration({
      episode,
      paths,
      sourceFile: paths.narrationSource,
      source: "elevenlabs",
      alignment: saved.alignment,
      timingSource: "elevenlabs",
      extra: { voiceId: saved.voiceId, modelId: saved.modelId, requestId: saved.requestId, characterCount: saved.characterCount },
    });
    ok(`Narration ready. Next: npm run render -- ${episode.id}`);
    return;
  }

  const apiKey = requireApiKey();
  if (!voice.isNarrator) warn(`This take uses voice ${describeVoice(voice)}, chosen by ${voice.source}.`);
  step(`Generating narration: ${text.length} characters, voice ${describeVoice(voice)}, model ${modelId}, language ${TTS.languageCode}`);
  const result = await synthesizeWithTimestamps({ ...request, apiKey });
  // Save everything ElevenLabs sent before doing anything else with it.
  ensureDir(paths.mediaDir);
  writeFileSync(paths.narrationSource, result.audio);
  saveTake(paths, paths.narrationSource, result.audio, {
    narrationHash: hash,
    text,
    voiceId: voice.voiceId,
    modelId,
    languageCode: TTS.languageCode,
    outputFormat: TTS.outputFormat,
    requestId: result.requestId,
    characterCount: result.characterCount,
    alignment: result.alignment,
    normalizedAlignment: result.normalizedAlignment,
  });
  ok(`Saved ${paths.narrationSource} (${(result.audio.length / 1024).toFixed(0)} KB, ${result.characterCount ?? "?"} characters billed)`);
  ok(`Saved ElevenLabs' timing and request details to ${paths.elevenlabsTake}, so this take can always be prepared again for free`);
  if (!result.alignment) warn("ElevenLabs returned no character timing; it will be estimated from pauses.");

  await prepareNarration({
    episode,
    paths,
    sourceFile: paths.narrationSource,
    source: "elevenlabs",
    alignment: result.alignment,
    timingSource: "elevenlabs",
    extra: { voiceId: voice.voiceId, modelId, requestId: result.requestId, characterCount: result.characterCount },
  });
  ok(`Narration ready. Next: npm run render -- ${episode.id}`);
});
