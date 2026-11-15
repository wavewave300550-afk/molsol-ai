/** Minecraft's script runtime provides a console (shown in the content log). */
declare const console: {
  log(...args: unknown[]): void;
  warn(...args: unknown[]): void;
  error(...args: unknown[]): void;
};
