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

/** Report a caught exception without ever throwing from a system callback. */
export function report(where: string, err: unknown): void {
  const msg = err instanceof Error ? `${err.message}\n${err.stack ?? ""}` : String(err);
  const s = current();
  if (s) s("error", { where, msg });
  console.warn(`[abm] error in ${where}: ${msg}`);
}
