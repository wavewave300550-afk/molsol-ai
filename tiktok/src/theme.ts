/**
 * Look and layout of every episode.
 *
 * Layout keeps clear of TikTok's own interface on a 1080×1920 frame: the
 * top bar (Following / For You), the caption and music bar at the bottom,
 * and the like / comment / share buttons down the right edge.
 */
export const COLORS = {
  background: "#070B1A",
  backgroundGlow: "#10204A",
  text: "#F8FAFC",
  muted: "#A5B4CB",
  accent: "#38BDF8",
  accent2: "#A3E635",
  accent3: "#F472B6",
  accent4: "#FBBF24",
  highlight: "#FDE047",
  card: "rgba(148, 163, 184, 0.10)",
  cardActive: "rgba(56, 189, 248, 0.16)",
  cardBorder: "rgba(148, 163, 184, 0.24)",
  test: "#EF4444",
} as const;

export const SERIES = [COLORS.accent, COLORS.accent2, COLORS.accent3, COLORS.accent4, "#A78BFA", "#2DD4BF"] as const;

export const LAYOUT = {
  left: 64,
  /** Wider right margin: TikTok's action buttons sit there. */
  right: 150,
  contentWidth: 1080 - 64 - 150,
  progressTop: 206,
  headerTop: 232,
  visualTop: 372,
  /** Two lines of subtitles reach up to about 1230. */
  visualBottom: 1210,
  /** Subtitles end here; TikTok's caption and music bar start below. */
  captionsBottom: 1440,
} as const;

/** CPK-style element colours, readable on the dark background. */
export const ELEMENT_COLORS: Record<string, string> = {
  H: "#F1F5F9",
  C: "#9CA3AF",
  N: "#60A5FA",
  O: "#F43F5E",
  F: "#86EFAC",
  Na: "#C084FC",
  Mg: "#34D399",
  P: "#FB923C",
  S: "#FACC15",
  Cl: "#4ADE80",
  K: "#A78BFA",
  Ca: "#CBD5E1",
  Fe: "#F97316",
};

/** Elements with light fills get dark symbol text. */
export const LIGHT_ELEMENTS = new Set(["H", "S", "F", "Ca", "Cl"]);
