/**
 * Which ElevenLabs voice narrates. The channel's permanent narrator
 * (TTS.narrator in src/lib/config.ts) is the default; a run only uses
 * another voice when one is given explicitly, and says so.
 */
import { TTS } from "../../src/lib/config.ts";

export type VoiceSource = "--voice option" | "ELEVENLABS_VOICE_ID" | "episode voice.voiceId" | "project default";
export type VoiceChoice = { voiceId: string; source: VoiceSource; isNarrator: boolean };

/** ElevenLabs voice ids are short alphanumeric strings, e.g. XAF1635HwW2TJGfbLzfc. */
const VOICE_ID = /^[A-Za-z0-9]{10,40}$/;

export function resolveVoice(input: { option?: string; env?: string; episode?: string }): VoiceChoice {
  const candidates: Array<[VoiceSource, string | undefined]> = [
    ["--voice option", input.option],
    ["ELEVENLABS_VOICE_ID", input.env],
    ["episode voice.voiceId", input.episode],
  ];
  for (const [source, raw] of candidates) {
    // Blank counts as unset: an unset GitHub Actions variable arrives as "".
    const voiceId = raw?.trim();
    if (!voiceId) continue;
    if (!VOICE_ID.test(voiceId)) throw new Error(`${source} is not a valid ElevenLabs voice id: "${voiceId}"`);
    return { voiceId, source, isNarrator: voiceId === TTS.narrator.voiceId };
  }
  return { voiceId: TTS.narrator.voiceId, source: "project default", isNarrator: true };
}

export function describeVoice(voice: VoiceChoice): string {
  return voice.isNarrator
    ? `${TTS.narrator.name} (${voice.voiceId})`
    : `${voice.voiceId}, not the channel narrator ${TTS.narrator.name}`;
}
