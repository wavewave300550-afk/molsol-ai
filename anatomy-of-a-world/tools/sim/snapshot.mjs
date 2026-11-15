// Dump the simulated arena (visible blocks + boss parts) for the three.js previews.
//   SIM_SNAPSHOT=1 node tools/sim/run.mjs   ->  tools/preview/out/<name>.bin / <name>.json
// The .bin has the same layout as tools/preview/voxels.mjs: int16 x, y, z + uint8 palette index.
import fs from "node:fs";
import path from "node:path";
import { BLOCK_COLORS, EMISSIVE, SMALL } from "../preview/blockcolors.mjs";

const NON_VISUAL = new Set(["minecraft:air", "minecraft:light_block_12", "minecraft:structure_void"]);

export function writeSnapshot(dim, box, outBase, parts) {
  const ids = ["minecraft:air"];
  const index = new Map([["minecraft:air", 0]]);
  const pal = (id) => {
    if (!index.has(id)) {
      index.set(id, ids.length);
      ids.push(id);
    }
    return index.get(id);
  };
  const solid = (x, y, z) => {
    const id = dim.getBlockId(x, y, z);
    return !NON_VISUAL.has(id) && !SMALL.has(id) && id !== "minecraft:water" && dim.isSolidAt(x, y, z);
  };
  const out = [];
  for (const [k, perm] of dim.blocks) {
    const id = perm.typeId;
    if (NON_VISUAL.has(id)) continue;
    const [x, y, z] = k.split(",").map(Number);
    if (x < box.x0 || x > box.x1 || z < box.z0 || z > box.z1 || y < box.y0 || y > box.y1) continue;
    if (!(!solid(x + 1, y, z) || !solid(x - 1, y, z) || !solid(x, y + 1, z) || !solid(x, y - 1, z) || !solid(x, y, z + 1) || !solid(x, y, z - 1))) continue;
    out.push(x, y, z, pal(id));
  }
  if (ids.length > 255) throw new Error(`snapshot: ${ids.length} block types do not fit a uint8 palette`);
  const buf = Buffer.alloc((out.length / 4) * 7);
  for (let i = 0, o = 0; i < out.length; i += 4, o += 7) {
    buf.writeInt16LE(out[i], o);
    buf.writeInt16LE(out[i + 1], o + 2);
    buf.writeInt16LE(out[i + 2], o + 4);
    buf.writeUInt8(out[i + 3], o + 6);
  }
  const meta = {
    palette: ids.map((id) => ({ id, color: id === "minecraft:air" ? null : (BLOCK_COLORS[id] ?? [255, 0, 255]), emissive: EMISSIVE.has(id), small: SMALL.has(id), water: id === "minecraft:water" })),
    parts: parts.map((e) => ({ typeId: e.typeId, pos: [e.location.x, e.location.y, e.location.z], yaw: e.getRotation().y, props: { ...e.props } })),
    visible: out.length / 4,
  };
  fs.mkdirSync(path.dirname(outBase), { recursive: true });
  fs.writeFileSync(outBase + ".bin", buf);
  fs.writeFileSync(outBase + ".json", JSON.stringify(meta));
  return meta;
}
