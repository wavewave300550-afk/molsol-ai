import { ADDON_NAME } from "../config.js";

const PREFIX = `[${ADDON_NAME}]`;

export function logInfo(message: string): void {
  console.log(`${PREFIX} ${message}`);
}

export function logWarn(message: string): void {
  console.warn(`${PREFIX} ${message}`);
}

export function logError(message: string): void {
  console.error(`${PREFIX} ${message}`);
}

export function describeError(error: unknown): string {
  if (error instanceof Error) return error.stack ? `${error.message}\n${error.stack}` : error.message;
  return String(error);
}

const MAX_REPORTS_PER_SOURCE = 3;
const reportCounts = new Map<string, number>();

/**
 * Logs an error thrown by content code (a creature hook, an ability, a phase...).
 * Each source is reported at most MAX_REPORTS_PER_SOURCE times so a hook that
 * fails every tick cannot flood the Content Log.
 */
export function reportContentError(source: string, error: unknown): void {
  const count = (reportCounts.get(source) ?? 0) + 1;
  reportCounts.set(source, count);
  if (count > MAX_REPORTS_PER_SOURCE) return;
  const suffix = count === MAX_REPORTS_PER_SOURCE ? " (further errors from this source are suppressed)" : "";
  logError(`${source} failed: ${describeError(error)}${suffix}`);
}

/** Runs content code, reporting instead of propagating errors so one creature cannot break the others. */
export function guarded<T>(source: string, fn: () => T): T | undefined {
  try {
    return fn();
  } catch (error) {
    reportContentError(source, error);
    return undefined;
  }
}
