/**
 * ElevenLabs text-to-speech with character timestamps.
 *
 * The API key is read from ELEVENLABS_API_KEY and only ever goes into the
 * request header. It is never logged, written to disk or passed on the
 * command line. Where it comes from:
 *   - GitHub Actions: repository secret ELEVENLABS_API_KEY
 *   - this computer: tiktok/.env (git-ignored), ELEVENLABS_API_KEY=...
 *   - Claude Code cloud sessions: an environment network secret for
 *     api.elevenlabs.io (the proxy adds the real key to each request);
 *     set ELEVENLABS_API_KEY to any placeholder so the script starts.
 */
import { type CharacterAlignment, normalizeAlignment } from "../../src/lib/alignment.ts";

export const ELEVENLABS_API = "https://api.elevenlabs.io";

export type TtsRequest = {
  apiKey: string;
  voiceId: string;
  modelId: string;
  text: string;
  languageCode?: string;
  voiceSettings: { stability: number; similarity_boost: number };
  outputFormat: string;
};

export type TtsResult = {
  audio: Buffer;
  alignment: CharacterAlignment | null;
  normalizedAlignment: CharacterAlignment | null;
  requestId: string | null;
  characterCount: string | null;
};

/**
 * The HTTP request for /v1/text-to-speech/{voice}/with-timestamps.
 * There is deliberately no speed setting: narration plays at its natural pace.
 */
export function buildTtsRequest(req: TtsRequest): { url: string; init: RequestInit } {
  const url = `${ELEVENLABS_API}/v1/text-to-speech/${encodeURIComponent(req.voiceId)}/with-timestamps?output_format=${encodeURIComponent(req.outputFormat)}`;
  const body: Record<string, unknown> = {
    text: req.text,
    model_id: req.modelId,
    voice_settings: { stability: req.voiceSettings.stability, similarity_boost: req.voiceSettings.similarity_boost },
    apply_text_normalization: "auto",
  };
  if (req.languageCode) body.language_code = req.languageCode;
  return {
    url,
    init: {
      method: "POST",
      headers: { "xi-api-key": req.apiKey, "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    },
  };
}

const HINTS: Record<number, string> = {
  401: "The API key was rejected. Check ELEVENLABS_API_KEY.",
  402: "This voice or model needs a paid ElevenLabs plan. Pick a pre-made voice (npm run voices) or upgrade.",
  422: "ElevenLabs rejected the request. Check the voice id and model id.",
  429: "Rate limit or quota reached. Wait and try again, or check the plan's character quota.",
};

async function failure(response: Response, what: string): Promise<Error> {
  let detail = "";
  try {
    detail = (await response.text()).slice(0, 300);
  } catch {
    // ignore
  }
  return new Error(`${what} failed with HTTP ${response.status}. ${HINTS[response.status] ?? ""} ${detail}`.trim());
}

export async function synthesizeWithTimestamps(req: TtsRequest, fetchImpl: typeof fetch = fetch): Promise<TtsResult> {
  const { url, init } = buildTtsRequest(req);
  const response = await fetchImpl(url, init);
  if (!response.ok) throw await failure(response, "ElevenLabs text-to-speech");
  const json = (await response.json()) as { audio_base64?: string; alignment?: unknown; normalized_alignment?: unknown };
  if (!json.audio_base64) throw new Error("ElevenLabs returned no audio.");
  return {
    audio: Buffer.from(json.audio_base64, "base64"),
    alignment: normalizeAlignment(json.alignment),
    normalizedAlignment: normalizeAlignment(json.normalized_alignment),
    requestId: response.headers.get("request-id"),
    characterCount: response.headers.get("x-character-count"),
  };
}

export type Voice = { voice_id: string; name: string; category?: string; labels?: Record<string, string> };

export async function listVoices(apiKey: string, fetchImpl: typeof fetch = fetch): Promise<Voice[]> {
  const response = await fetchImpl(`${ELEVENLABS_API}/v1/voices`, { headers: { "xi-api-key": apiKey } });
  if (!response.ok) throw await failure(response, "Listing ElevenLabs voices");
  return ((await response.json()) as { voices: Voice[] }).voices;
}

export function requireApiKey(): string {
  const key = process.env.ELEVENLABS_API_KEY?.trim();
  if (!key) {
    throw new Error(
      "ELEVENLABS_API_KEY is not set, so no narration can be generated.\n" +
        "  • GitHub Actions: add the repository secret ELEVENLABS_API_KEY.\n" +
        "  • This computer: put ELEVENLABS_API_KEY=... in tiktok/.env (git-ignored).\n" +
        "  • Claude Code cloud session: save the key as an environment secret for api.elevenlabs.io,\n" +
        "    then run with ELEVENLABS_API_KEY=injected-by-proxy.\n" +
        "  To test everything else without a key: npm run pipeline:test",
    );
  }
  return key;
}
