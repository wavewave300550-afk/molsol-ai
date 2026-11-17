/**
 * Copies the Thai fonts used by the videos from the @fontsource packages into
 * public/fonts/, so renders never depend on a font CDN or on fonts installed
 * on the machine (GitHub runners have no Thai fonts by default).
 *
 * Usage: npm run fonts:sync
 */
import { copyFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { FONT_FILES } from "../src/lib/fonts-manifest.ts";
import { projectRoot } from "./lib/paths.ts";

const target = join(projectRoot, "public", "fonts");
mkdirSync(target, { recursive: true });

const packages: Record<string, string> = {
  Kanit: "@fontsource/kanit",
  "Noto Sans Thai": "@fontsource/noto-sans-thai",
};

for (const font of FONT_FILES) {
  const source = join(projectRoot, "node_modules", packages[font.family], "files", font.file);
  copyFileSync(source, join(target, font.file));
}
copyFileSync(join(projectRoot, "node_modules/@fontsource/kanit/LICENSE"), join(target, "Kanit-OFL.txt"));
copyFileSync(
  join(projectRoot, "node_modules/@fontsource/noto-sans-thai/LICENSE"),
  join(target, "NotoSansThai-OFL.txt"),
);
console.log(`Copied ${FONT_FILES.length} font files and 2 licenses to public/fonts/`);
