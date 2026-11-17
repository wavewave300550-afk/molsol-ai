/**
 * Lists the ElevenLabs voices this API key can use (read-only, no credits)
 * and marks the channel narrator, Madame Scientia. To use another voice for
 * one take: npm run narrate -- <id> --voice <voice-id>
 *
 * Usage: npm run voices
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
    const current = v.voice_id === TTS.narrator.voiceId ? "  ← channel narrator" : v.voice_id === process.env.ELEVENLABS_VOICE_ID?.trim() ? "  ← ELEVENLABS_VOICE_ID" : "";
    console.log(`${v.voice_id}  ${v.name.padEnd(24)} ${(v.category ?? "").padEnd(12)} ${labels}${current}`);
  }
  console.log(
    `\n${voices.length} voices. Narration uses ${TTS.narrator.name} (${TTS.narrator.voiceId}) with model ${TTS.modelId}, language "${TTS.languageCode}".`,
  );
});
