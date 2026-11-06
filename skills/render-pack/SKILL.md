---
name: render-pack
description: Use when the user asks for a video, motion graphic, animation, animated explainer, kinetic typography, slideshow, Remotion/Manim/Blender/3D render, or anything whose rendering would be slow in this sandbox. Write the full project and package it as a "render pack" zip that renders in about a minute on the user's own computer, instead of rendering the whole video here. Also use in Claude Code to create a pack in a folder.
---

# render-pack

This sandbox has ~2 CPU cores and no GPU, so a render that takes 30–60 minutes here takes
about a minute on the user's laptop. **You write the project; the user's machine renders it.**

**Never render the full video here.** At most, render ONE low-resolution preview frame to
sanity-check the look.

All commands below use `scripts/build_pack.py` from this skill's folder.

## 1. Pick an engine

| Engine | Use for |
|---|---|
| `html-canvas` | Kinetic type, UI/product motion, charts, canvas/WebGL, CSS animation. **Default for 2D motion graphics.** |
| `remotion` | React motion graphics, data-driven or templated video |
| `blender` | 3D scenes, product shots, abstract 3D loops |
| `manim` | Math and explainer animations |
| `ffmpeg` | Slideshows, image sequences, stills + music (no code runs: lowest risk) |

Then read the engine's authoring guide (rules for that engine):
`python3 scripts/build_pack.py guide <engine>`

## 2. Write the pack

```
python3 scripts/build_pack.py init <dir> --engine <engine> --title "<Title>" \
        [--width 1920 --height 1080 --fps 30 --duration 6]
```

This creates `<dir>/render.json`. Then write `src/` (code) and `assets/` (images, fonts,
audio) by following the guide. Edit `render.json` for `description`, `audio`, and
`engine_options`. Field reference: [references/manifest.md](references/manifest.md).

Rules for every engine:
- Animation is a **pure function of time/frame**. No wall-clock time, unseeded randomness
  or network access at render time.
- Bundle every asset in the pack. Use only assets you made or that the user supplied.
- Keep the pack small (under ~50 MB); compress large images.

## 3. Optional preview (one frame)

`python3 scripts/build_pack.py preview <dir> --time <seconds>` renders `preview.png` at 25%
size if the engine's tools exist here. If it fails because a tool is missing, skip it: don't
install Blender, browsers or Manim just for a preview. Look at the image; fix and repeat if
it's wrong.

## 4. Build the zip

`python3 scripts/build_pack.py build <dir> --out <outputs>/<slug>-render-pack.zip`

In claude.ai, `<outputs>` is `/mnt/user-data/outputs`. `build` adds `runtime/`,
`run.sh`, `run.ps1` and a plain-language `README.md`, validates against the schema, and zips.
Fix any validation error it reports and build again.

## 5. Tell the user how to render it

Keep it short:
1. Download the zip.
2. **Easiest:** open Claude Code in the download folder and say *"render this video pack"*
   (needs the `render-run` skill / local-render plugin).
3. **Or by hand:** unzip, open a terminal in the folder, run `sh run.sh` (Mac/Linux) or
   `powershell -ExecutionPolicy Bypass -File run.ps1` (Windows).

Say which tools they need (from `render.json` `requires`) and roughly how long the render
should take. If you rendered a preview, show it.
