/**
 * Script approval. A reviewer approves the scientific script before any
 * narration is generated; the approval stores a hash of the reviewed content,
 * so editing the narration, visuals or sources afterwards voids it.
 */
import { createHash } from "node:crypto";
import type { Episode } from "../../src/lib/schema.ts";
import { normalizeNarration } from "../../src/lib/text.ts";

/** JSON with object keys sorted at every level, so equal content hashes equally. */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${canonicalJson(v)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

const sha256 = (text: string) => createHash("sha256").update(text, "utf8").digest("hex");

/**
 * Hash of everything a reviewer approves: narration, visuals, sources,
 * duration tier. The voice is not part of it (it does not change the facts).
 */
export function contentHash(episode: Episode): string {
  const { approval: _approval, voice: _voice, $schema: _schema, ...content } = episode;
  return sha256(canonicalJson(content));
}

/** Hash of only the spoken words; narration audio is valid while this matches. */
export function narrationHash(episode: Episode): string {
  return sha256(canonicalJson(episode.scenes.map((s) => ({ id: s.id, narration: normalizeNarration(s.narration) }))));
}

export type ApprovalStatus = { approved: true } | { approved: false; reason: string };

export function approvalStatus(episode: Episode): ApprovalStatus {
  const approval = episode.approval;
  if (!approval) return { approved: false, reason: "The script has not been approved yet." };
  if (approval.contentHash !== contentHash(episode)) {
    return {
      approved: false,
      reason: `The script changed after ${approval.approvedBy} approved it on ${approval.approvedAt}. Review and approve it again.`,
    };
  }
  if (approval.durationTier !== episode.durationTier) {
    return { approved: false, reason: `Approval covers the "${approval.durationTier}" tier, not "${episode.durationTier}".` };
  }
  return { approved: true };
}
