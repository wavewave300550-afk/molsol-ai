import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";
import { FONT_FILES } from "./lib/fonts-manifest.ts";

// loadFont() holds the render (delayRender) until every file has loaded, so
// no frame is captured with a fallback font or missing Thai glyphs.
for (const font of FONT_FILES) {
  loadFont({
    family: font.family,
    url: staticFile(`fonts/${font.file}`),
    weight: font.weight,
    unicodeRange: font.unicodeRange,
    display: "block",
  });
}

export const HEADING_FONT = "Kanit, 'Noto Sans Thai', sans-serif";
export const BODY_FONT = "'Noto Sans Thai', Kanit, sans-serif";
