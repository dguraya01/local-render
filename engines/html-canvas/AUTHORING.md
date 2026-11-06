# html-canvas: authoring guide

Best for kinetic typography, UI/product motion, charts, canvas 2D or WebGL, CSS animation.
Frames are captured in headless Chrome at exact times, then encoded with ffmpeg.

## Files

```
render.json          entry: "src/index.html"
src/index.html       the page (sized to the video, e.g. 1920x1080, no scrollbars)
src/main.js          animation code (classic <script src>, or type="module" — both work)
assets/              fonts, images, audio (reference them as ../assets/... from src/)
```

The page is served from `http://127.0.0.1:<port>/` with the pack folder as the root, so
relative URLs, ES modules and `fetch()` of local files all work. There is no internet
access requirement: bundle every font and image in `assets/`.

## The one rule: time is an input

The capturer seeks the page to time `t` (seconds) for every frame. Your animation must be a
pure function of `t`.

```js
const DURATION = 6;
function renderFrame(t) {      // draw the whole frame for time t
  ctx.clearRect(0, 0, W, H);
  /* ... */
}
window.renderFrame = renderFrame;          // the capturer calls this (may return a Promise)

if (!window.__LR_CAPTURE__) {              // only play in real time in a normal browser
  const t0 = performance.now();
  const loop = (now) => { renderFrame(((now - t0) / 1000) % DURATION); requestAnimationFrame(loop); };
  requestAnimationFrame(loop);
} else {
  renderFrame(0);
}
```

- **CSS animations / Web Animations** need no code: the capturer pauses every animation in
  `document.getAnimations()` and sets `currentTime = t`. Use `animation-delay` for sequencing.
- **No** `Date.now()`, `performance.now()` or `setTimeout` inside the drawing path.
- **Random:** use a seeded PRNG (e.g. `s = (s * 16807) % 2147483647`).
- **Async setup** (fonts, images, WebGL): set `window.lrReady = promise` and the capturer
  waits for it (it already waits for `document.fonts.ready`).
- Size the canvas to the video's exact pixel size (`width="1920" height="1080"`).

## render.json engine_options

| key | default | meaning |
|---|---|---|
| `frame_format` | `"png"` | `"jpeg"` is faster for photographic content |

Optional `"audio": "assets/music.mp3"` is muxed in and faded out at the end.

## Preview inside the sandbox

`build_pack.py preview <dir> --time 2.5` needs Node, npm and a Chrome/Chromium. If the
sandbox has none, skip the preview; never install a browser just for it.
