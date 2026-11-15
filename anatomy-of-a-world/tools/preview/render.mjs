// Headless preview driver: serves the viewer + assets, runs a "shot list" script in Chromium.
//   import { withViewer } from "./render.mjs"; await withViewer(async (page, shot) => { ... });
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const MOUNTS = {
  "/web/": path.join(HERE, "web"),
  "/three/": path.join(ROOT, "node_modules", "three"),
  "/out/": path.join(HERE, "out"),
  "/rp/": path.join(ROOT, "build", "packs", "RP"),
};
const TYPES = { ".js": "text/javascript", ".mjs": "text/javascript", ".html": "text/html", ".json": "application/json", ".png": "image/png", ".bin": "application/octet-stream" };

function serve() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const url = decodeURIComponent(req.url.split("?")[0]);
      for (const [m, dir] of Object.entries(MOUNTS)) {
        if (!url.startsWith(m)) continue;
        const f = path.join(dir, url.slice(m.length));
        if (!f.startsWith(dir) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) break;
        res.writeHead(200, { "content-type": TYPES[path.extname(f)] ?? "application/octet-stream" });
        fs.createReadStream(f).pipe(res);
        return;
      }
      res.writeHead(404);
      res.end("not found " + url);
    });
    srv.listen(0, "127.0.0.1", () => resolve(srv));
  });
}

export async function withViewer(fn, { width = 1280, height = 800 } = {}) {
  const srv = await serve();
  const port = srv.address().port;
  const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") console.log("[page]", m.type(), m.text());
  });
  page.on("pageerror", (e) => console.log("[pageerror]", e.message));
  await page.goto(`http://127.0.0.1:${port}/web/viewer.html`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  const shot = async (file, cam) => {
    await page.evaluate((c) => window.preview.render(c), cam);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    await page.locator("canvas").screenshot({ path: file });
  };
  try {
    await fn(page, shot, port);
  } finally {
    await browser.close();
    srv.close();
  }
}
