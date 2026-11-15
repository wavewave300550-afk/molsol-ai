// Generate a mountain with the real (compiled) generator and export the visible voxels
// as a compact binary blob for the three.js preview renderer.
//   node tools/preview/voxels.mjs <out.bin> [--phase2] [--layout=1]
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { BLOCK_COLORS, EMISSIVE, SMALL } from "./blockcolors.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const gen = await import(pathToFileURL(path.join(ROOT, "build/scripts/gen/mountain.js")).href);
const pal = await import(pathToFileURL(path.join(ROOT, "build/scripts/gen/palette.js")).href);

export async function buildMountainVoxels({ phase2 = false, layout = 0 } = {}) {
  const t0 = Date.now();
  const m = new gen.MountainModel().generate();
  const genMs = Date.now() - t0;
  const g = m.g;
  if (phase2) applyPhase2(m, gen, pal, layout);
  const entries = pal.paletteEntries();
  const colors = entries.map((e) => BLOCK_COLORS[e.id] ?? (e.id.includes("light_block") ? null : [255, 0, 255]));
  const missing = entries.filter((e) => BLOCK_COLORS[e.id] === undefined).map((e) => e.id);
  const solid = (b) => b > 1 && colors[b] && !SMALL.has(entries[b].id) && entries[b].id !== "minecraft:water";
  const out = [];
  let count = 0;
  const counts = new Map();
  for (let x = g.x0; x < g.x0 + g.sx; x++)
    for (let z = g.z0; z < g.z0 + g.sz; z++)
      for (let y = g.y0; y < g.y0 + g.sy; y++) {
        const b = m.grid[m.idx(x, y, z)];
        if (b <= 1) continue;
        count++;
        counts.set(entries[b].id, (counts.get(entries[b].id) ?? 0) + 1);
        if (!colors[b]) continue;
        const vis = !solid(m.get(x + 1, y, z)) || !solid(m.get(x - 1, y, z)) || !solid(m.get(x, y + 1, z)) || !solid(m.get(x, y - 1, z)) || !solid(m.get(x, y, z + 1)) || !solid(m.get(x, y, z - 1));
        if (!vis) continue;
        out.push(x, y, z, b);
      }
  const buf = Buffer.alloc((out.length / 4) * 7);
  for (let i = 0, o = 0; i < out.length; i += 4, o += 7) {
    buf.writeInt16LE(out[i], o);
    buf.writeInt16LE(out[i + 1], o + 2);
    buf.writeInt16LE(out[i + 2], o + 4);
    buf.writeUInt8(out[i + 3], o + 6);
  }
  const meta = {
    palette: entries.map((e, i) => ({ id: e.id, color: colors[i], emissive: EMISSIVE.has(e.id), small: SMALL.has(e.id), water: e.id === "minecraft:water" })),
    nodes: m.nodes,
    legs: m.legs,
    summit: m.summit,
    tunnelMouth: m.tunnelMouth,
    waterfalls: m.waterfalls,
    trees: m.trees.length,
    totalBlocks: count,
    visible: out.length / 4,
    genMs,
    missing,
    counts: Object.fromEntries([...counts.entries()].sort((a, b) => b[1] - a[1])),
  };
  return { buf, meta, model: m };
}

/** Mirror of the runtime Great Unfolding result (cut + disk), for previews. */
export function applyPhase2(m, genMod, palMod, layout) {
  const g = m.g;
  const cut = m.phase2CutY();
  for (let x = g.x0; x < g.x0 + g.sx; x++)
    for (let z = g.z0; z < g.z0 + g.sz; z++) {
      const c = m.col(x, z);
      if (!(m.flags[c] & 1)) continue;
      const top = m.top[c];
      if (top > cut) {
        for (let y = cut + 1; y < g.y0 + g.sy; y++) m.set(x, y, z, palMod.AIR);
        for (let y = cut - 4; y <= cut; y++) if (m.get(x, y, z) > 1) m.set(x, y, z, m.dorsalBlock(x, y, z, cut));
      }
      for (let y = g.y0; y < g.y0 + g.sy; y++) {
        const b = m.phase2Block(x, y, z, layout);
        if (b >= 0) m.set(x, y, z, b);
      }
    }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const outPath = process.argv[2] ?? path.join(HERE, "out", "mountain.bin");
  const phase2 = process.argv.includes("--phase2");
  const layout = process.argv.includes("--layout=1") ? 1 : 0;
  const { buf, meta } = await buildMountainVoxels({ phase2, layout });
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  fs.writeFileSync(outPath.replace(/\.bin$/, ".json"), JSON.stringify(meta, null, 1));
  console.log(`voxels: ${meta.visible} visible / ${meta.totalBlocks} total, trees ${meta.trees}, gen ${meta.genMs} ms`);
  if (meta.missing.length) console.log("missing colours:", meta.missing.join(", "));
  console.log("nodes:", JSON.stringify(meta.nodes.map((n) => [n.id, n.pos])));
  console.log("summit:", JSON.stringify(meta.summit), "tunnel:", JSON.stringify(meta.tunnelMouth), "falls:", JSON.stringify(meta.waterfalls));
  console.log("top blocks:", Object.entries(meta.counts).slice(0, 14).map(([k, v]) => `${k.replace("minecraft:", "")}=${v}`).join(" "));
}
