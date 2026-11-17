/**
 * Lists the ElevenLabs voices this API key can use, to pick a Thai narrator.
 * Pre-made voices work on every plan; Voice Library voices need a paid plan.
 *
 * Usage: npm run voices
 * Then set ELEVENLABS_VOICE_ID (or "voice": { "voiceId": ... } in an episode).
 */
import { TTS } from "../src/lib/config.ts";
import { runCli } from "./lib/cli.ts";
import { listVoices, requireApiKey } from "./lib/elevenlabs.ts";

runCli(async () => {
  const voices = await listVoices(requireApiKey());
  voices.sort((a, b) => (a.category === "premade" ? -1 : 0) - (b.category === "premade" ? -1 : 0));
  for (const v of voices) {
    const labels = Object.entries(v.labels ?? {})
      .map(([k, value]) => `${k}: ${value}`)
      .join(", ");
    const current = v.voice_id === (process.env.ELEVENLABS_VOICE_ID ?? TTS.defaultVoiceId) ? "  ← current" : "";
    console.log(`${v.voice_id}  ${v.name.padEnd(24)} ${(v.category ?? "").padEnd(12)} ${labels}${current}`);
  }
  console.log(`\n${voices.length} voices. Thai narration uses model ${TTS.modelId} with language "${TTS.languageCode}".`);
});
