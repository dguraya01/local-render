// Frame-accurate capture of an HTML/CSS/JS animation with Playwright.
//
// The page is served from a local 127.0.0.1 server rooted at the pack folder.
// For every frame we seek the page to time t (seconds):
//   1. call window.renderFrame(t) if the page defines it (canvas / JS animations)
//   2. pause every CSS/Web Animation and set its currentTime to t
// then screenshot. Pages see window.__LR_CAPTURE__ === true and must not run
// their own real-time loop in that case.
//
// node capture.mjs --root DIR --entry src/index.html --width W --height H --fps F
//                  --frames N --out DIR [--workers K]
// node capture.mjs ... --single T --scale 0.25 --png out.png      (one preview frame)
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright-core";

const argv = process.argv.slice(2);
const opt = {};
for (let i = 0; i < argv.length; i += 2) opt[argv[i].replace(/^--/, "")] = argv[i + 1];
const root = path.resolve(opt.root);
const width = parseInt(opt.width, 10);
const height = parseInt(opt.height, 10);
const fps = parseFloat(opt.fps);
const workers = Math.max(1, parseInt(opt.workers || "1", 10));
const fmt = opt.format === "jpeg" ? "jpeg" : "png";

const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml", ".webp": "image/webp", ".gif": "image/gif", ".woff": "font/woff",
  ".woff2": "font/woff2", ".ttf": "font/ttf", ".otf": "font/otf", ".mp3": "audio/mpeg",
  ".wav": "audio/wav", ".mp4": "video/mp4", ".webm": "video/webm",
};

function serve() {
  const server = http.createServer((req, res) => {
    const urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
    const file = path.resolve(root, "." + urlPath);
    if (file !== root && !file.startsWith(root + path.sep)) { res.writeHead(403); return res.end(); }
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); return res.end("not found"); }
      res.writeHead(200, { "content-type": MIME[path.extname(file).toLowerCase()] || "application/octet-stream" });
      res.end(data);
    });
  });
  return new Promise((ok) => server.listen(0, "127.0.0.1", () => ok(server)));
}

async function launch() {
  const base = { headless: true, args: ["--force-color-profile=srgb", "--hide-scrollbars", "--mute-audio"] };
  const attempts = [];
  if (process.env.LR_CHROME) attempts.push({ ...base, executablePath: process.env.LR_CHROME });
  attempts.push({ ...base, channel: "chrome" }, { ...base, channel: "msedge" }, { ...base });
  let last;
  for (const a of attempts) {
    try { return await chromium.launch(a); } catch (e) { last = e; }
  }
  throw new Error("Could not start Chrome, Edge or Chromium. Install Google Chrome, or run " +
    "`npx playwright install chromium` inside runtime/.\n" + (last && last.message));
}

async function openPage(browser, url, scale) {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: scale });
  await context.addInitScript(() => { window.__LR_CAPTURE__ = true; });
  const page = await context.newPage();
  page.on("pageerror", (e) => console.error("page error: " + e.message));
  await page.goto(url, { waitUntil: "load" });
  await page.evaluate(async () => {
    await document.fonts.ready;
    if (window.lrReady) await window.lrReady;
  });
  return page;
}

async function seek(page, t) {
  await page.evaluate(async (t) => {
    if (typeof window.renderFrame === "function") await window.renderFrame(t);
    for (const a of document.getAnimations()) { a.pause(); a.currentTime = t * 1000; }
  }, t);
}

const server = await serve();
const url = `http://127.0.0.1:${server.address().port}/${opt.entry}`;
const browser = await launch();
try {
  if (opt.single !== undefined) {
    const page = await openPage(browser, url, parseFloat(opt.scale || "0.25"));
    await seek(page, parseFloat(opt.single));
    await page.screenshot({ path: opt.png, type: "png" });
  } else {
    const total = parseInt(opt.frames, 10);
    fs.mkdirSync(opt.out, { recursive: true });
    let done = 0;
    const work = async (w) => {
      const page = await openPage(browser, url, 1);
      for (let i = w; i < total; i += workers) {
        await seek(page, i / fps);
        const name = `frame_${String(i + 1).padStart(6, "0")}.${fmt}`;
        await page.screenshot({ path: path.join(opt.out, name), type: fmt, ...(fmt === "jpeg" ? { quality: 95 } : {}) });
        done++;
        if (done % 5 === 0 || done === total) console.log(`PROGRESS ${done} ${total}`);
      }
    };
    await Promise.all(Array.from({ length: Math.min(workers, total) }, (_, w) => work(w)));
  }
} finally {
  await browser.close();
  server.close();
}
