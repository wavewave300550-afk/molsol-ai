// Prints track stats and writes an SVG map (debug aid for layout work).
import { writeFileSync } from 'node:fs';
import { Track } from '../src/sim/track.js';
import { RIFT_JUNCTION } from '../src/sim/trackData.js';
const t = new Track(RIFT_JUNCTION);
console.log('length', t.length.toFixed(1), 'samples', t.n, 'step', t.step.toFixed(3));
const bySec = {};
for (const s of t.samples) {
  const r = Math.abs(s.curv) > 1e-5 ? 1 / Math.abs(s.curv) : 9999;
  const b = (bySec[s.sec] ??= { minR: 9999, at: 0, len: 0 });
  b.len += t.step;
  if (r < b.minR) { b.minR = r; b.at = s.u; }
}
for (const [k, v] of Object.entries(bySec)) console.log(k, 'len', v.len.toFixed(0), 'minR', v.minR.toFixed(1), 'at u', v.at.toFixed(2));
const b = t.branch;
console.log('branch len', b.length.toFixed(1), 'main between', b.mainLength.toFixed(1), 'saves', (b.mainLength - b.length).toFixed(1), 'gap', b.gap0.toFixed(1), b.gap1.toFixed(1));
console.log('gates', t.gates.map((g) => g.s.toFixed(0)).join(' '));
const out = process.argv[2];
if (out) {
  let L = '', R = '', C = '';
  for (const s of t.samples) {
    C += `${s.x.toFixed(1)},${(-s.z).toFixed(1)} `;
    L += `${(s.x - s.rx * s.hw).toFixed(1)},${(-(s.z - s.rz * s.hw)).toFixed(1)} `;
    R += `${(s.x + s.rx * s.hw).toFixed(1)},${(-(s.z + s.rz * s.hw)).toFixed(1)} `;
  }
  const g = t.gates.map((g) => { const s = t.samples[g.i]; return `<line x1="${s.x - s.rx * s.hw}" y1="${-(s.z - s.rz * s.hw)}" x2="${s.x + s.rx * s.hw}" y2="${-(s.z + s.rz * s.hw)}" stroke="red" stroke-width="1.5"/>`; }).join('');
  const br = `<line x1="${b.ax}" y1="${-b.az}" x2="${b.ax + b.tx * b.length}" y2="${-(b.az + b.tz * b.length)}" stroke="orange" stroke-width="${b.hw * 2}" opacity="0.5"/>`;
  writeFileSync(out, `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-60 -260 560 520" width="1120" height="1040"><rect x="-60" y="-260" width="560" height="520" fill="#223"/>${br}<polygon points="${L}" fill="none" stroke="#fff"/><polygon points="${R}" fill="none" stroke="#8cf"/><polygon points="${C}" fill="none" stroke="#555" stroke-dasharray="3 3"/>${g}</svg>`);
}
