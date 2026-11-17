import { Easing, interpolate } from "remotion";

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0 → 1 over `length` frames starting at `start`. */
export const progress = (frame: number, start: number, length = 14): number =>
  interpolate(frame, [start, start + length], [0, 1], { ...clamp, easing: EASE_OUT });

/** Springy 0 → 1 for things that pop in (atoms, tiles). */
export const pop = (frame: number, start: number, length = 18): number =>
  interpolate(frame, [start, start + length], [0, 1], { ...clamp, easing: Easing.spring({ damping: 12 }) });

export const formatNumber = (value: number, decimals = 0): string =>
  new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
    useGrouping: Math.abs(value) >= 10000,
  }).format(value);
