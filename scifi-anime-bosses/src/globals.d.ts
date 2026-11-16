/** The Bedrock script runtime provides a console (it is not part of the ES lib). */
declare const console: {
  log(...args: unknown[]): void;
  warn(...args: unknown[]): void;
  error(...args: unknown[]): void;
};
