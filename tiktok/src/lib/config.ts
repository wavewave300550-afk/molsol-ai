/**
 * Production settings shared by the Node scripts and the Remotion composition.
 * Plain TypeScript (no React, no Node APIs) so both sides can import it.
 */

/** Output format every episode is rendered in. */
export const VIDEO = { width: 1080, height: 1920, fps: 30 } as const;

/**
 * Allowed final video lengths (seconds). Standard episodes must land in
 * 60-90 s. Complex episodes may run up to 120 s, but only when the episode
 * declares durationTier "complex" with a justification and that is approved.
 * If narration does not fit, the script must be changed: the system never
 * speeds up, compresses or cuts narration to make it fit.
 */
export const DURATION_TIERS = {
  standard: { minSeconds: 60, maxSeconds: 90 },
  complex: { minSeconds: 60, maxSeconds: 120 },
} as const;

export const TIMELINE = {
  /** Silence kept after the last word so the ending is not abrupt. */
  tailSeconds: 0.8,
  /** A new scene's visuals start this long before its first spoken word. */
  sceneLeadSeconds: 0.12,
  /** Scenes shorter than this are rejected (the script needs more narration). */
  minSceneSeconds: 1.5,
};

export const CAPTIONS = {
  /** Longest caption page, counted in visible Thai/Latin characters. */
  maxChars: 28,
  /** A phrase break (space in the script) ends a page once it has this many. */
  minCharsAtPhraseBreak: 10,
  /** A pause longer than this always starts a new page. */
  pauseBreakMs: 450,
  /** Longest time one page stays on screen while speech continues. */
  maxPageMs: 3200,
  /** How long the last page of a phrase stays after its last word. */
  holdMs: 350,
};

export const TTS = {
  provider: "elevenlabs",
  /**
   * The channel's permanent Thai narrator: an existing ElevenLabs voice that
   * every episode uses unless a run explicitly picks another (--voice,
   * ELEVENLABS_VOICE_ID or voice.voiceId in an episode). The pipeline only
   * reads and speaks with voices; it never creates, edits or replaces one.
   */
  narrator: { name: "Madame Scientia", voiceId: "XAF1635HwW2TJGfbLzfc", language: "th" },
  /** Highest-quality ElevenLabs model, 90+ languages including Thai. */
  modelId: "eleven_v4",
  languageCode: "th",
  outputFormat: "mp3_44100_128",
  /** eleven_v4 accepts only stability and similarity_boost (no speed). */
  voiceSettings: { stability: 0.7, similarity_boost: 0.75 },
  /** One request carries the whole narration; longer scripts are rejected. */
  maxCharactersPerRequest: 5000,
};

/** Loudness target for TikTok (EBU R128 integrated loudness). */
export const AUDIO_MASTER = { integratedLufs: -14, truePeakDb: -1.5, loudnessRange: 11, sampleRate: 48000 };

/**
 * Rough speaking-rate model used only to warn about script length before
 * narration exists. The real narration duration always wins.
 */
export const ESTIMATE = { weightedCharsPerSecond: 13, phrasePauseSeconds: 0.25, scenePauseSeconds: 0.6 };

/**
 * Narrator voice tests (kind "voice-test"): short samples to hear the voice,
 * never published. They replace the 60-120 s episode rule with their own
 * limits; the text cap keeps each test cheap (ElevenLabs bills per character).
 */
export const VOICE_TEST = { minSeconds: 5, maxSeconds: 30, maxCharacters: 400 };
