/** Logging that ends up in the Content Log (console.warn/error) with a stable prefix. */
const PREFIX = "[Grimoire]";

function fmt(e: unknown): string {
  if (e instanceof Error) return `${e.name}: ${e.message}${e.stack ? "\n" + e.stack : ""}`;
  return String(e);
}

export const log = {
  /** Debug output only when the debug flag is enabled (kept quiet in normal play). */
  debugEnabled: false,
  debug(...parts: unknown[]): void {
    if (this.debugEnabled) console.warn(PREFIX, ...parts.map((p) => (typeof p === "string" ? p : JSON.stringify(p))));
  },
  warn(...parts: unknown[]): void {
    console.warn(PREFIX, ...parts.map((p) => (typeof p === "string" ? p : fmt(p))));
  },
  error(msg: string, e?: unknown): void {
    console.error(PREFIX, msg, e === undefined ? "" : fmt(e));
  },
};
