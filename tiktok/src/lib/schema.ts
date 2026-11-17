/**
 * The episode script format (episodes/<id>/episode.json).
 *
 * One file holds everything that must be scientifically reviewed: the Thai
 * narration of each scene, what each scene shows, and the sources behind
 * every claim. Approval is recorded in the same file and covers a hash of
 * all of it, so any edit after approval requires a new approval.
 */
import { z } from "zod";

const slug = z.string().regex(/^[a-z0-9][a-z0-9-]*$/, "use lowercase letters, digits and hyphens");
const text = z.string().trim().min(1);

export const SourceSchema = z.strictObject({
  id: slug,
  /** Short label shown on screen while the scene plays, e.g. "PubChem: Water". */
  label: text,
  /** Full reference, used on the end card and in the TikTok description. */
  citation: text,
  url: z.url().optional(),
  doi: z
    .string()
    .regex(/^10\.\d{4,9}\/\S+$/, "DOI like 10.1021/ci9901338")
    .optional(),
  /** Date someone opened the source and confirmed the claim (YYYY-MM-DD). */
  accessed: z.iso.date().optional(),
  note: z.string().optional(),
});

export const CueSchema = z.strictObject({
  id: slug,
  /** Exact words in the scene narration; the cue fires when they are spoken. */
  text,
  /** Which occurrence of the words, if they appear more than once (1-based). */
  occurrence: z.number().int().min(1).optional(),
});

const AtomSchema = z.strictObject({
  id: z.string().min(1),
  element: z.string().regex(/^[A-Z][a-z]?$/, "element symbol like H, O, Na"),
  /** Position in any units; the scene scales the molecule to fit. */
  x: z.number(),
  y: z.number(),
  label: z.string().optional(),
});

const BondSchema = z.strictObject({
  from: z.string(),
  to: z.string(),
  order: z.union([z.literal(1), z.literal(2), z.literal(3)]).optional(),
});

export const VisualSchema = z.discriminatedUnion("type", [
  z.strictObject({
    type: z.literal("title"),
    title: text,
    subtitle: z.string().optional(),
    kicker: z.string().optional(),
  }),
  z.strictObject({
    type: z.literal("molecule"),
    title: text,
    /** Chemical formula written plainly, e.g. "H2O"; digits render as subscripts. */
    formula: z.string().optional(),
    atoms: z.array(AtomSchema).min(1).max(40),
    bonds: z.array(BondSchema),
    /** cue id -> atom ids that appear when the cue's words are spoken. */
    reveal: z.record(z.string(), z.array(z.string())).optional(),
    caption: z.string().optional(),
  }),
  z.strictObject({
    type: z.literal("chart"),
    title: text,
    unit: text,
    bars: z
      .array(
        z.strictObject({
          label: text,
          sublabel: z.string().optional(),
          value: z.number(),
          cue: z.string().optional(),
        }),
      )
      .min(1)
      .max(6),
    note: z.string().optional(),
    decimals: z.number().int().min(0).max(4).optional(),
  }),
  z.strictObject({
    type: z.literal("process"),
    title: text,
    steps: z
      .array(z.strictObject({ label: text, detail: z.string().optional(), cue: z.string().optional() }))
      .min(2)
      .max(6),
  }),
  z.strictObject({
    type: z.literal("fact"),
    title: text,
    items: z
      .array(
        z.strictObject({
          value: z.number(),
          decimals: z.number().int().min(0).max(4).optional(),
          prefix: z.string().optional(),
          suffix: z.string().optional(),
          label: text,
          cue: z.string().optional(),
        }),
      )
      .min(1)
      .max(4),
  }),
  z.strictObject({
    type: z.literal("image"),
    title: z.string().optional(),
    /** File under public/, e.g. "illustrations/cell.svg". */
    src: text,
    alt: text,
    /** Who made the image and under which licence. */
    credit: text,
  }),
  z.strictObject({ type: z.literal("sources"), title: text }),
]);

export const SceneSchema = z.strictObject({
  id: slug,
  /** Short section label shown at the top of the frame. */
  label: text,
  /** Thai narration: spoken by the voice and shown as subtitles, word for word. */
  narration: text,
  visual: VisualSchema,
  sourceIds: z.array(z.string()).default([]),
  /** Set to false for scenes that make no scientific claim (intro, outro, call to action). */
  factual: z.boolean().default(true),
  cues: z.array(CueSchema).default([]),
});

export const ApprovalSchema = z.strictObject({
  approvedBy: text,
  approvedAt: z.iso.datetime({ offset: true }),
  /** SHA-256 of the reviewed content (everything except approval and voice). */
  contentHash: z.string().regex(/^[0-9a-f]{64}$/),
  durationTier: z.enum(["standard", "complex"]),
  notes: z.string().optional(),
});

export const EpisodeSchema = z.strictObject({
  $schema: z.string().optional(),
  schemaVersion: z.literal(1),
  id: slug,
  /**
   * "episode": a real episode. "pipeline-test": a full test render (TEST
   * badge). "voice-test": a short narration sample to hear the narrator,
   * with its own length limits (VOICE_TEST); never published.
   */
  kind: z.enum(["episode", "pipeline-test", "voice-test"]),
  title: text,
  language: z.literal("th"),
  /** standard = 60-90 s. complex = up to 120 s, needs a justification and approval. */
  durationTier: z.enum(["standard", "complex"]),
  complexJustification: z.string().optional(),
  voice: z
    .strictObject({
      voiceId: z.string().optional(),
      modelId: z.string().optional(),
      stability: z.number().min(0).max(1).optional(),
      similarityBoost: z.number().min(0).max(1).optional(),
    })
    .optional(),
  /** Extra terms subtitles must not split (see src/lib/glossary.ts). */
  glossary: z.array(text).optional(),
  sources: z.array(SourceSchema),
  scenes: z.array(SceneSchema).min(2).max(14),
  approval: ApprovalSchema.nullable().optional(),
});

export type Source = z.infer<typeof SourceSchema>;
export type Cue = z.infer<typeof CueSchema>;
export type Visual = z.infer<typeof VisualSchema>;
export type Scene = z.infer<typeof SceneSchema>;
export type Approval = z.infer<typeof ApprovalSchema>;
export type Episode = z.infer<typeof EpisodeSchema>;
export type DurationTier = Episode["durationTier"];
export type EpisodeKind = Episode["kind"];

export function formatSchemaError(error: z.ZodError): string {
  return error.issues
    .map((issue) => `  - ${issue.path.length ? issue.path.join(".") : "(root)"}: ${issue.message}`)
    .join("\n");
}
