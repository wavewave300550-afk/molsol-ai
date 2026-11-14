// Headless test runner: bundles src/main.ts against the mock Script API and runs the suites.
//   node tests/run.mjs            -> all suites
//   node tests/run.mjs controls   -> only suites whose file name contains "controls"
//   node tests/run.mjs spells dw01,dn03   -> spell suite limited to some spells
import { build } from "esbuild";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(here, ".out");
fs.mkdirSync(path.join(out, "node_modules/@minecraft/server"), { recursive: true });
fs.writeFileSync(path.join(out, "node_modules/@minecraft/server/package.json"), JSON.stringify({ name: "@minecraft/server", type: "module", main: "index.mjs" }));
fs.writeFileSync(path.join(out, "node_modules/@minecraft/server/index.mjs"), `export * from ${JSON.stringify(pathToFileURL(path.join(here, "mock/server.mjs")).href)};\n`);
const [filter, arg] = process.argv.slice(2);
const wanted = filter === "spells" && arg ? arg.split(",") : null;
const isolate = {
  name: "isolate-spells",
  setup(b) {
    // spell-filtered runs do not exercise the book presentation (another slice owns it)
    b.onLoad({ filter: /[\\/]core[\\/]books\.ts$/ }, () => (wanted
      ? { loader: "ts", contents: "export function installBooks(): void {}" } : undefined));
    b.onLoad({ filter: /[\\/]spells[\\/](dw|dn|ed)\d\d_[^\\/]*\.ts$/ }, (args) => {
      const id = path.basename(args.path).slice(0, 4);
      if (!wanted || wanted.includes(id)) return undefined;
      return { loader: "ts", resolveDir: path.dirname(args.path),
        contents: `import { defineSpell } from "../core/registry";\nexport default defineSpell("${id}", (c) => { c.scene.endAt(1); });` };
    });
  },
};
await build({ entryPoints: [path.join(here, "../src/main.ts")], bundle: true, format: "esm", target: "es2022",
  external: ["@minecraft/server"], outfile: path.join(out, `main_${process.pid}.mjs`), logLevel: "error", plugins: [isolate] });

const mock = await import(pathToFileURL(path.join(here, "mock/server.mjs")).href);
mock.loadAssets();
const warnings = [];
const origWarn = console.warn;
console.warn = (...a) => { warnings.push(a.join(" ")); };
await import(pathToFileURL(path.join(out, `main_${process.pid}.mjs`)).href);
fs.rmSync(path.join(out, `main_${process.pid}.mjs`), { force: true });
const commands = mock.startup();

let failed = 0, passed = 0;
const ctx = {
  mock, warnings, commands,
  test(name, fn) {
    const w0 = warnings.length;
    try {
      fn();
      const fresh = warnings.slice(w0).filter((w) => w.includes("[grimoire]"));
      if (fresh.length) throw new Error("script warnings: " + fresh.slice(0, 3).join(" | "));
      passed++;
      console.log(`  ok   ${name}`);
    } catch (e) {
      failed++;
      console.log(`  FAIL ${name}\n       ${String(e.stack || e).split("\n").slice(0, 4).join("\n       ")}`);
    }
  },
  eq(a, b, msg = "") { if (a !== b) throw new Error(`${msg} expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`); },
  ok(v, msg = "assertion failed") { if (!v) throw new Error(msg); },
};
ctx.arg = arg;
for (const f of fs.readdirSync(here).filter((f) => f.endsWith(".test.mjs")).sort()) {
  if (filter ? !f.includes(filter) : f.includes("trace")) continue;   // the scene recorder only runs on request
  console.log(f);
  const suite = await import(pathToFileURL(path.join(here, f)).href);
  await suite.default(ctx);
}
console.warn = origWarn;
console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
