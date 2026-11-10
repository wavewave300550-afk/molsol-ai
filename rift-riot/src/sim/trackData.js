// RIFT JUNCTION — ชุมทางมิติหลุด
// One closed loop made of four dimension-themed sections plus one shortcut branch.
// Control points are (x, z) on the ground plane, y = height, hw = half road width.
// Point 0 is the start/finish line. Driving direction follows the array order.

export const RIFT_JUNCTION = {
  id: 'rift-junction',
  name: 'RIFT JUNCTION',
  nameTh: 'ชุมทางมิติหลุด',
  points: [
    // ── Section 1: Junction Plaza (wide start, learn to accelerate) ──
    { x: 0, z: 0, y: 0, hw: 11, sec: 'plaza' },
    { x: 0, z: 70, y: 0, hw: 11, sec: 'plaza' },
    { x: 0, z: 138, y: 0, hw: 9.5, sec: 'plaza' },
    { x: 16, z: 190, y: 0.3, hw: 9, sec: 'plaza' },
    { x: 58, z: 216, y: 1.2, hw: 8.5, sec: 'plaza' },
    // ── Section 2: Giant Tea Party Road (flowing bends, sliding teacups) ──
    { x: 120, z: 208, y: 3, hw: 8.5, sec: 'tea' },
    { x: 178, z: 172, y: 5, hw: 8.5, sec: 'tea' },
    { x: 240, z: 182, y: 7, hw: 8.5, sec: 'tea' },
    { x: 292, z: 218, y: 9, hw: 8.5, sec: 'tea' },
    { x: 345, z: 214, y: 10, hw: 8.5, sec: 'tea' },
    // ── Section 3: Shattered Dimension Bridge (open edges, shortcut gap) ──
    { x: 375, z: 172, y: 10, hw: 8.5, sec: 'bridge' },
    { x: 375, z: 125, y: 10, hw: 8.5, sec: 'bridge' }, // 11 = junction A
    { x: 398, z: 88, y: 10, hw: 8.5, sec: 'bridge' },
    { x: 435, z: 58, y: 10, hw: 8.5, sec: 'bridge' },
    { x: 450, z: 20, y: 10, hw: 8.5, sec: 'bridge' },
    { x: 435, z: -18, y: 10, hw: 8.5, sec: 'bridge' },
    { x: 398, z: -48, y: 10, hw: 8.5, sec: 'bridge' },
    { x: 375, z: -85, y: 10, hw: 8.5, sec: 'bridge' }, // 17 = junction B
    { x: 375, z: -130, y: 10, hw: 8.5, sec: 'bridge' },
    // ── Section 4: S-bends and the run back to the line ──
    { x: 354, z: -182, y: 9, hw: 8.5, sec: 'neon' },
    { x: 298, z: -200, y: 7.2, hw: 8.5, sec: 'neon' },
    { x: 250, z: -160, y: 5.4, hw: 8.5, sec: 'neon' },
    { x: 196, z: -150, y: 3.8, hw: 8.5, sec: 'neon' },
    { x: 150, z: -204, y: 2.2, hw: 8.5, sec: 'neon' },
    { x: 92, z: -224, y: 0.9, hw: 8.5, sec: 'neon' },
    { x: 34, z: -206, y: 0.2, hw: 9, sec: 'neon' },
    { x: 2, z: -156, y: 0, hw: 9.5, sec: 'plaza' },
    { x: 0, z: -80, y: 0, hw: 10.5, sec: 'plaza' },
  ],
  // Walls are removed between these control points (the bridge floats over the rift).
  open: { from: 11.15, to: 16.85 },
  // Shortcut: a straight span from junction A to junction B with a gap in the middle.
  branch: { from: 11, to: 17, hw: 6.5, gapCenter: 0.5 },
  // Mandatory gates (control-point parameters). None inside the shortcut interval.
  gates: [0, 2.2, 4.6, 7, 9.4, 10.75, 17.3, 19.5, 21.5, 23.5, 25.6],
  // Sliding teacups: where (control-point parameter), sweep amplitude, period, phase.
  teacups: [
    { u: 5.55, amp: 4.6, period: 5.2, phase: 0.0 },
    { u: 6.6, amp: 4.4, period: 4.4, phase: 1.9 },
    { u: 7.75, amp: 4.6, period: 5.6, phase: 3.6 },
  ],
  sections: {
    plaza: { name: 'ลานชุมทาง', nameEn: 'Junction Plaza' },
    tea: { name: 'ถนนงานเลี้ยงน้ำชายักษ์', nameEn: 'Giant Tea Party Road' },
    bridge: { name: 'สะพานมิติแตก', nameEn: 'Shattered Dimension Bridge' },
    neon: { name: 'โค้งตัวเอส', nameEn: 'S-Bend Boulevard' },
  },
};
