/**
 * Reuses an ElevenLabs take that was already paid for, without contacting
 * ElevenLabs: for example the MP3 kept in the artifact of a GitHub Actions run
 * whose mastering step failed. The take is mastered, checked sample for sample
 * and timed exactly like a new one from `npm run narrate`.
 *
 * Usage: npm run narration:recover -- <episode-id> <take.mp3> [--take <elevenlabs-take.json>] [--from "<where it came from>"]
 *   --take   the elevenlabs-take.json saved with the MP3 (saved by every
 *            narration since it was introduced). It brings back ElevenLabs'
 *            character timing, voice, model and request id, and proves the
 *            MP3 and the script are the ones the take was made with.
 *   --from   where the MP3 came from, e.g. "GitHub Actions run 44044487202".
 *            Required without --take; kept in narration.json.
 *   Without --take the timing is estimated from the pauses, and the voice and
 *   model are the ones `npm run narrate` uses (--voice / --model to change).
 *
 * Needs no API key and spends no credits.
 */
import { copyFileSync, existsSync, readFileSync } from "node:fs";
import { basename, extname, join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { TTS } from "../src/lib/config.ts";
import { formatIssues, hasErrors } from "../src/lib/issues.ts";
import { validateEpisode } from "../src/lib/rules.ts";
import { approvalStatus, narrationHash } from "./lib/approval.ts";
import { ok, runCli, warn } from "./lib/cli.ts";
import { loadEpisode, publicFileExists } from "./lib/episode-io.ts";
import { prepareNarration } from "./lib/narration.ts";
import { ensureDir } from "./lib/paths.ts";
import { readSavedTake, type SavedTake, sha256, takeProblems } from "./lib/take.ts";
import { resolveVoice } from "./lib/voice.ts";

runCli(async () => {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: { take: { type: "string" }, from: { type: "string" }, voice: { type: "string" }, model: { type: "string" } },
  });
  const { episode, paths } = loadEpisode(positionals[0]);
  const file = positionals[1];
  if (!file) throw new Error(`Give the MP3: npm run narration:recover -- ${paths.id} <take.mp3> [--take elevenlabs-take.json]`);
  if (!existsSync(file)) throw new Error(`Audio file not found: ${file}`);

  const issues = validateEpisode(episode, { publicFileExists });
  if (hasErrors(issues)) throw new Error(`The script has errors:\n${formatIssues(issues)}`);
  const status = approvalStatus(episode);
  if (!status.approved) throw new Error(`Narration is only used for an approved script. ${status.reason}`);

  const audio = readFileSync(file);
  const audioSha256 = sha256(audio);
  let take: SavedTake | null = null;
  if (values.take) {
    if (values.voice || values.model) throw new Error("--voice and --model are only for a take without its timing file; --take already names them.");
    take = readSavedTake(values.take);
    const problems = takeProblems(take, { narrationHash: narrationHash(episode), audioSha256 });
    if (problems.length) throw new Error(`Cannot use ${values.take}: ${problems.join("; ")}.`);
  } else if (!values.from?.trim()) {
    throw new Error('Say where the MP3 came from, e.g. --from "GitHub Actions run 44044487202", or give its --take file.');
  }

  const voiceId = take?.voiceId ?? resolveVoice({ option: values.voice, env: process.env.ELEVENLABS_VOICE_ID, episode: episode.voice?.voiceId }).voiceId;
  const modelId = take?.modelId ?? (values.model?.trim() || episode.voice?.modelId || TTS.modelId);
  if (voiceId !== TTS.narrator.voiceId) warn(`This take is recorded as voice ${voiceId}, not the channel narrator ${TTS.narrator.name}.`);

  // Keep the take where `npm run narrate` keeps one, with its timing file.
  ensureDir(paths.mediaDir);
  const stored = join(paths.mediaDir, `narration.source${extname(file).toLowerCase() || ".mp3"}`);
  if (resolve(file) !== resolve(stored)) copyFileSync(file, stored);
  if (values.take && resolve(values.take) !== resolve(paths.elevenlabsTake)) copyFileSync(values.take, paths.elevenlabsTake);

  const from = values.from?.trim() || `saved take ${basename(values.take ?? "")}`;
  ok(`Recovering the take from ${from} (SHA-256 ${audioSha256.slice(0, 12)}…): nothing is sent to ElevenLabs.`);
  if (!take?.alignment) warn("ElevenLabs' character timing was not saved with this take: it is estimated from the pauses (accurate to the phrase).");
  await prepareNarration({
    episode,
    paths,
    sourceFile: stored,
    source: "elevenlabs",
    alignment: take?.alignment ?? null,
    timingSource: "elevenlabs",
    extra: {
      voiceId,
      modelId,
      requestId: take?.requestId ?? null,
      characterCount: take?.characterCount ?? null,
      recovered: { from, audioSha256, at: new Date().toISOString() },
    },
  });
  const next = episode.kind === "voice-test" ? `npm run voice-test -- ${paths.id} --report` : `npm run render -- ${paths.id}`;
  ok(`Narration ready from the recovered take, without new credits. Next: ${next}`);
});
