// The Bedrock script runtime provides `console` (output goes to the Content Log).
declare const console: {
  log(...args: unknown[]): void;
  warn(...args: unknown[]): void;
  error(...args: unknown[]): void;
};
