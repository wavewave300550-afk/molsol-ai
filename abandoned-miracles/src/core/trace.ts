/**
 * Lightweight instrumentation. The headless simulation installs a sink to
 * assert on what happened; in game it only prints when debug is on.
 */
import { CONFIG } from "../config";

export type TraceSink = (kind: string, data: Record<string, unknown>) => void;

let sink: TraceSink | undefined;

export function setTraceSink(s: TraceSink | undefined): void {
  sink = s;
}

function current(): TraceSink | undefined {
  return sink ?? (globalThis as { __abmTrace?: TraceSink }).__abmTrace;
}

export function trace(kind: string, data: Record<string, unknown> = {}): void {
  const s = current();
  if (s) s(kind, data);
  else if (CONFIG.debug && kind !== "hazard") console.warn(`[abm] ${kind} ${JSON.stringify(data)}`);
}

/** True when a test harness is listening (lets hot paths skip building trace payloads in game). */
export function tracing(): boolean {
  return current() !== undefined;
}

const seenErrors = new Map<string, number>();
let announced = 0;
let notifier: ((line: string) => void) | undefined;

/** Where the first occurrence of each distinct failure is shown to players (set once at start-up). */
export function setErrorNotifier(f: ((line: string) => void) | undefined): void {
  notifier = f;
}

/**
 * Report a caught exception without ever throwing from a system callback.
 *
 * A failure inside a per-tick path would otherwise print twenty lines a second. Each distinct
 * failure is logged in full once, then only every 200th time with a count; its first occurrence
 * is also shown in chat (at most six different ones per session) so it can be reported.
 */
export function report(where: string, err: unknown): void {
  const head = (err instanceof Error ? err.message : String(err)).split("\n")[0];
  const msg = err instanceof Error ? `${err.message}\n${err.stack ?? ""}` : String(err);
  const s = current();
  if (s) s("error", { where, msg });
  const key = `${where}|${head}`;
  const n = (seenErrors.get(key) ?? 0) + 1;
  seenErrors.set(key, n);
  if (n === 1) {
    console.warn(`[abm] error in ${where}: ${msg}`);
    if (notifier && announced < 6) {
      announced++;
      try {
        notifier(`\u00a77[The Abandoned Miracles] internal problem in \u00a7f${where}\u00a77: ${head}`);
      } catch {
        /* reporting must never fail */
      }
    }
  } else if (n % 200 === 0) {
    console.warn(`[abm] error in ${where} (x${n}): ${head}`);
  }
}
