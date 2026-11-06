// "Write in the cloud. Render at home." — 6 s kinetic-type motion graphic.
// Everything is a pure function of time t (seconds): renderFrame(t) draws one frame.
// local-render calls window.renderFrame(t) for each frame; in a normal browser it plays in real time.
(function () {
  const W = 1920, H = 1080, DURATION = 6;
  const canvas = document.getElementById("c");
  const ctx = canvas.getContext("2d");

  const C = { ink: "#0b0d17", ink2: "#151a2e", lime: "#c6ff3d", coral: "#ff5c39", paper: "#f4f1ea", mute: "#7d84a3" };
  const FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif';

  // ---- helpers
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const seg = (t, a, b) => clamp((t - a) / (b - a));
  const easeOut = (x) => 1 - Math.pow(1 - x, 4);
  const easeInOut = (x) => (x < 0.5 ? 8 * x ** 4 : 1 - Math.pow(-2 * x + 2, 4) / 2);
  const back = (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const lerp = (a, b, x) => a + (b - a) * x;

  // seeded PRNG so every render is identical
  let s = 1337;
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const dots = Array.from({ length: 140 }, () => ({ x: rand() * W, y: rand() * H, r: 1 + rand() * 2.5, sp: 0.3 + rand(), ph: rand() * 6.28 }));

  function text(str, x, y, size, color, weight = 800, align = "left", alpha = 1, track = 0) {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = color;
    ctx.font = `${weight} ${size}px ${FONT}`;
    ctx.textAlign = align;
    ctx.textBaseline = "alphabetic";
    if ("letterSpacing" in ctx) ctx.letterSpacing = `${track}px`;
    ctx.fillText(str, x, y);
    ctx.restore();
  }

  // Masked word that slides up from a baseline
  function reveal(str, x, y, size, color, p, align = "left") {
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, y - size * 1.05, W, size * 1.3);
    ctx.clip();
    text(str, x, y + (1 - easeOut(p)) * size * 1.2, size, color, 900, align, 1, -size * 0.04);
    ctx.restore();
  }

  function background(t) {
    const g = ctx.createRadialGradient(W * 0.7, H * 0.3, 50, W * 0.5, H * 0.5, W * 0.8);
    g.addColorStop(0, C.ink2);
    g.addColorStop(1, C.ink);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    // drifting particle field
    for (const d of dots) {
      const x = (d.x + t * 40 * d.sp) % W;
      const y = d.y + Math.sin(t * 1.3 + d.ph) * 12;
      ctx.globalAlpha = 0.25 + 0.25 * Math.sin(t * 2 + d.ph);
      ctx.fillStyle = C.mute;
      ctx.beginPath();
      ctx.arc(x, y, d.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function bar(label, sub, y, fill, color, tLabel, p) {
    const x = 260, w = 1400, h = 46;
    text(label, x, y - 26, 34, C.paper, 700, "left", p);
    text(sub, x + w, y - 26, 28, C.mute, 500, "right", p);
    ctx.globalAlpha = p;
    ctx.fillStyle = "#232a45";
    roundRect(x, y, w, h, 23);
    ctx.fillStyle = color;
    roundRect(x, y, Math.max(h, w * fill), h, 23);
    ctx.globalAlpha = 1;
    text(tLabel, x + Math.max(h, w * fill) + 24, y + 36, 38, color, 800, "left", p);
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.fill();
  }

  function renderFrame(t) {
    t = clamp(t, 0, DURATION);
    background(t);

    // ---- Act 1 (0 - 2.2s): WRITE / in the cloud.
    const out1 = easeInOut(seg(t, 1.9, 2.3));
    if (t < 2.3) {
      ctx.save();
      ctx.translate(0, -out1 * 120);
      ctx.globalAlpha = 1 - out1;
      reveal("WRITE", 200, 560, 300, C.paper, seg(t, 0.1, 0.8));
      reveal("in the cloud.", 210, 700, 96, C.mute, seg(t, 0.45, 1.1));
      // underline sweep
      ctx.fillStyle = C.coral;
      ctx.fillRect(210, 740, 760 * easeOut(seg(t, 0.8, 1.5)), 10);
      ctx.restore();
    }

    // ---- Act 2 (2.0 - 3.9s): RENDER / at home.
    const in2 = seg(t, 2.0, 2.7), out2 = easeInOut(seg(t, 3.5, 3.9));
    if (t >= 2.0 && t < 3.9) {
      ctx.save();
      ctx.translate(0, -out2 * 120);
      ctx.globalAlpha = 1 - out2;
      reveal("RENDER", 200, 560, 300, C.lime, in2);
      reveal("at home.", 210, 700, 96, C.paper, seg(t, 2.35, 3.0));
      ctx.fillStyle = C.lime;
      ctx.fillRect(210, 740, 520 * easeOut(seg(t, 2.7, 3.3)), 10);
      ctx.restore();
    }

    // ---- Act 3 (3.7 - 6s): race between the cloud sandbox and your laptop
    if (t >= 3.7) {
      const p = easeOut(seg(t, 3.7, 4.1));
      text("SAME VIDEO. TWO MACHINES.", 260, 330, 30, C.mute, 700, "left", p, 6);
      const race = seg(t, 4.0, 5.0);
      const laptop = easeInOut(race);
      const cloud = laptop / 45; // 45x slower
      const done = laptop >= 1;
      bar("Cloud sandbox", "2 CPU cores, no GPU", 470, cloud, C.coral, done ? "2% … ~45 min" : `${Math.round(cloud * 100)}%`, p);
      bar("Your laptop", "Apple Silicon + VideoToolbox", 640, laptop, C.lime, done ? "~1 min ✓" : `${Math.round(laptop * 100)}%`, p);

      // end card
      const e = back(seg(t, 5.0, 5.5));
      ctx.save();
      ctx.globalAlpha = clamp(e);
      text("local-render", 260, 900 + (1 - clamp(e)) * 30, 72, C.paper, 900, "left", clamp(e), -2);
      ctx.fillStyle = C.lime;
      ctx.fillRect(260, 922, 470 * clamp(e), 8);
      text("Claude writes it. Your machine renders it.", 1660, 900, 32, C.mute, 500, "right", clamp(e));
      ctx.restore();
    }

    // subtle vignette + frame counter dot
    ctx.fillStyle = C.lime;
    ctx.beginPath();
    ctx.arc(W - 90, 90, 8 + 3 * Math.sin(t * 6), 0, Math.PI * 2);
    ctx.fill();
  }

  window.renderFrame = renderFrame;
  if (!window.__LR_CAPTURE__) {
    const start = performance.now();
    const loop = (now) => { renderFrame(((now - start) / 1000) % DURATION); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  } else {
    renderFrame(0);
  }
})();
