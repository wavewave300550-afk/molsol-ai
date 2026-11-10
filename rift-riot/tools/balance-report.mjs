// Headless all-AI races: prints finish order, times, skill uses and falls.
// Usage: node tools/balance-report.mjs [races=20] [verbose]
import { Track } from '../src/sim/track.js';
import { RIFT_JUNCTION } from '../src/sim/trackData.js';
import { Race } from '../src/sim/race.js';
import { BALANCE } from '../src/data/balance.js';

const N = Number(process.argv[2] || 20);
const verbose = process.argv.includes('verbose');
const track = new Track(RIFT_JUNCTION);
const agg = {};
const dt = BALANCE.race.fixedDt;
for (let k = 0; k < N; k++) {
  const race = new Race(track, { playerId: null, seed: 1000 + k * 7919 });
  let guard = 0;
  const ev = {};
  while (!race.done && guard++ < 60 * 400) {
    race.step(dt);
    for (const e of race.events) ev[e.type] = (ev[e.type] || 0) + 1;
    race.events.length = 0;
  }
  if (verbose) console.log(`race ${k}: t=${race.time.toFixed(1)}`, JSON.stringify(ev));
  for (const r of race.ranking) {
    const a = (agg[r.def.id] ??= { wins: 0, placeSum: 0, timeSum: 0, n: 0, dnf: 0, uses: 0, falls: 0, best: 1e9, level: 0 });
    if (!r.finished) { a.dnf++; continue; }
    a.n++;
    a.placeSum += r.place;
    a.timeSum += r.finishTime;
    a.uses += r.sk.uses;
    a.falls += r.falls;
    a.best = Math.min(a.best, ...r.lapTimes);
    if (r.place === 1) a.wins++;
    if (verbose) console.log(`  ${r.place}. ${r.def.id.padEnd(10)} ${r.finishTime.toFixed(2)}s lvl=${r.ai.level} laps=${r.lapTimes.map((t) => t.toFixed(1)).join('/')} skill×${r.sk.uses} falls=${r.falls}`);
  }
}
console.log('racer       wins  avgPlace  avgTime  bestLap  skill/race  falls/race  dnf');
for (const [id, a] of Object.entries(agg)) {
  console.log(`${id.padEnd(11)} ${String(a.wins).padStart(4)}  ${(a.placeSum / a.n).toFixed(2).padStart(8)}  ${(a.timeSum / a.n).toFixed(1).padStart(7)}  ${a.best.toFixed(1).padStart(7)}  ${(a.uses / a.n).toFixed(1).padStart(10)}  ${(a.falls / a.n).toFixed(2).padStart(10)}  ${a.dnf}`);
}
