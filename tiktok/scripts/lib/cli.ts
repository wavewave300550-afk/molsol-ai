/** Runs a script's main function and turns thrown errors into a clean exit 1. */
export function runCli(main: () => Promise<void> | void): void {
  Promise.resolve()
    .then(main)
    .catch((error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`\n✖ ${message}`);
      if (process.env.DEBUG && error instanceof Error) console.error(error.stack);
      process.exit(1);
    });
}

export const step = (message: string): void => console.log(`\n▶ ${message}`);
export const ok = (message: string): void => console.log(`✔ ${message}`);
export const warn = (message: string): void => console.log(`⚠ ${message}`);
