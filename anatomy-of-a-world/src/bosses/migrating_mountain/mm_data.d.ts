/** Type declarations for the generated data module (tools/export_mountain.mjs). */
import type { LegSite, NodeSite, TreeInfo, V3, WaterfallSite } from "../../gen/mountain.js";
export interface MountainExport {
  v: number;
  seed: number;
  grid: { x0: number; y0: number; z0: number; sx: number; sy: number; sz: number };
  cols: string;
  top: string;
  under: string;
  caveTop: string;
  flags: string;
  p2box: { x0: number; y0: number; z0: number; sx: number; sy: number; sz: number };
  p2a: string;
  p2b: string;
  trees: TreeInfo[];
  nodes: NodeSite[];
  legs: LegSite[];
  waterfalls: WaterfallSite[];
  pathPoints: V3[];
  summit: V3;
  tunnelMouth: V3;
}
export declare const MM_DATA: MountainExport;
