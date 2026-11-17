/**
 * Font files bundled in public/fonts/ (SIL Open Font License, see the
 * *-OFL.txt files there). Each weight ships as a Thai and a Latin subset that
 * load under one family name, split by unicode range like Google Fonts does.
 */
export const THAI_RANGE = "U+02D7,U+0303,U+0331,U+0E01-0E5B,U+200C-200D,U+25CC";
export const LATIN_RANGE =
  "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD";

export type FontFile = {
  family: "Kanit" | "Noto Sans Thai";
  weight: string;
  unicodeRange: string;
  file: string;
};

const variants: Array<[FontFile["family"], string, string]> = [
  ["Kanit", "kanit", "500"],
  ["Kanit", "kanit", "700"],
  ["Kanit", "kanit", "800"],
  ["Noto Sans Thai", "noto-sans-thai", "400"],
  ["Noto Sans Thai", "noto-sans-thai", "600"],
];

export const FONT_FILES: FontFile[] = variants.flatMap(([family, slug, weight]) => [
  { family, weight, unicodeRange: THAI_RANGE, file: `${slug}-thai-${weight}-normal.woff2` },
  { family, weight, unicodeRange: LATIN_RANGE, file: `${slug}-latin-${weight}-normal.woff2` },
]);
