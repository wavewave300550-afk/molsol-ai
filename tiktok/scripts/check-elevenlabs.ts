/**
 * Checks the ElevenLabs setup without generating any audio:
 *  - whether ELEVENLABS_API_KEY is present (its value is never printed);
 *  - which voice narration will use (the narrator, unless overridden);
 *  - with --online: read-only requests for that voice's details and the
 *    plan's character usage, confirming the key works and can use the voice.
 * It never calls text-to-speech, so no characters are billed.
 *
 * Usage: npm run elevenlabs:check [-- --online]
 * GitHub: Actions > ElevenLabs check > Run workflow (uses the repository secret).
 */
import { appendFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { TTS } from "../src/lib/config.ts";
import { runCli } from "./lib/cli.ts";
import { ELEVENLABS_API } from "./lib/elevenlabs.ts";
import { describeVoice, resolveVoice } from "./lib/voice.ts";

const HOW_TO_ADD =
  "Add the key as a GitHub Actions secret: repository Settings > Secrets and variables > Actions > " +
  "New repository secret, name ELEVENLABS_API_KEY, value = your ElevenLabs API key. Then run Actions > ElevenLabs check again.";

type VoiceDetails = {
  name?: string;
  category?: string;
  labels?: Record<string, string>;
  verified_languages?: Array<{ language?: string; model_id?: string; accent?: string }>;
};

runCli(async () => {
  const { values } = parseArgs({ options: { online: { type: "boolean", default: false } } });
  const report: string[] = [];
  const line = (text: string) => {
    console.log(text);
    report.push(text);
  };
  const voice = resolveVoice({ env: process.env.ELEVENLABS_VOICE_ID });
  const key = process.env.ELEVENLABS_API_KEY?.trim();
  let problem: string | null = key ? null : "ELEVENLABS_API_KEY is not set.";

  line(`Narrator voice: ${describeVoice(voice)}, from ${voice.source}`);
  line(`Model: ${TTS.modelId}, language ${TTS.languageCode}`);
  line(`ELEVENLABS_API_KEY: ${key ? "set (value hidden)" : "NOT SET"}`);

  if (key && values.online) {
    const headers = { "xi-api-key": key };
    const voiceResponse = await fetch(`${ELEVENLABS_API}/v1/voices/${encodeURIComponent(voice.voiceId)}`, { headers });
    const body = voiceResponse.ok ? "" : await voiceResponse.text();
    if (voiceResponse.ok) {
      const details = (await voiceResponse.json()) as VoiceDetails;
      line(`Key accepted. Voice found: "${details.name}" (${details.category ?? "category unknown"})`);
      const labels = Object.entries(details.labels ?? {})
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
      if (labels) line(`Voice labels: ${labels}`);
      if (details.verified_languages?.length) {
        line(`Verified languages: ${details.verified_languages.map((l) => `${l.language}${l.model_id ? ` (${l.model_id})` : ""}`).join(", ")}`);
      }
      if (voice.isNarrator && details.name !== TTS.narrator.name) {
        line(`Note: the voice is named "${details.name}" in ElevenLabs, not "${TTS.narrator.name}". Check the voice id.`);
      }
    } else if (voiceResponse.status === 401 && body.includes("missing_permissions")) {
      line("Key accepted, but it may not read voice details (voices_read permission). Narration can still work.");
    } else if (voiceResponse.status === 401) {
      problem = "ElevenLabs rejected the key (HTTP 401). The secret is set but its value is wrong or revoked.";
      line(problem);
    } else if (voiceResponse.status === 404 || body.includes("voice_not_found")) {
      problem = `This key's ElevenLabs account cannot use voice ${voice.voiceId} (HTTP 404). Use a key from the account that has ${TTS.narrator.name}.`;
      line(problem);
    } else {
      problem = `The voice lookup failed with HTTP ${voiceResponse.status}: ${body.slice(0, 200)}`;
      line(problem);
    }

    if (!problem) {
      const usage = await fetch(`${ELEVENLABS_API}/v1/user/subscription`, { headers });
      if (usage.ok) {
        const plan = (await usage.json()) as { tier?: string; character_count?: number; character_limit?: number };
        line(`Plan: ${plan.tier ?? "unknown"}, ${plan.character_count ?? "?"} of ${plan.character_limit ?? "?"} characters used this period`);
      } else {
        line(`Plan usage: not readable with this key (HTTP ${usage.status}); narration does not need it.`);
      }
    }
  } else if (key) {
    line("The key was not tested. Add --online for read-only checks (no audio, no credits).");
  }

  if (process.env.GITHUB_STEP_SUMMARY) {
    const status = problem ? "**Not ready.**" : "**Ready for narration.**";
    appendFileSync(process.env.GITHUB_STEP_SUMMARY, `## ElevenLabs configuration\n\n${status}\n\n${report.map((l) => `- ${l}`).join("\n")}\n${problem && !key ? `\n${HOW_TO_ADD}\n` : ""}`);
  }
  if (problem) throw new Error(key ? problem : `${problem}\n${HOW_TO_ADD}`);
  console.log(values.online ? "\n✔ ElevenLabs is ready for narration." : "\n✔ Configuration found (not tested online).");
});
