# Direct mode: describe → pack → render

Use this when the user explains a video to you in Claude Code and has no pack yet.

## 1. Pin down the video (ask only what's missing)

- What it shows and the message or story, beat by beat
- Length (default 6–10 s), aspect ratio (16:9 1920x1080, 9:16 1080x1920, 1:1 1080x1080), fps (30)
- Look: colors, fonts, mood; any logos, images or audio they will supply
- Where it will be used (social post, product page, slide), which hints at format

Propose an engine (see below) and a one-line storyboard per beat. Confirm before writing code.

| Engine | Use for |
|---|---|
| `html-canvas` | 2D motion graphics, kinetic type, UI motion (default) |
| `remotion` | React projects, data-driven/templated video |
| `blender` | 3D |
| `manim` | Math/explainers |
| `ffmpeg` | Slideshows, stills + music |

## 2. Write the pack

Pick a new folder the user agrees on, e.g. `./<slug>-render-pack`.

```
python3 scripts/build_pack.py guide <engine>       # engine rules: read before writing code
python3 scripts/build_pack.py init <folder> --engine <engine> --title "<Title>" \
        --width 1920 --height 1080 --fps 30 --duration 8
# write src/ and assets/ following the guide; fill description / engine_options
python3 scripts/build_pack.py finalize <folder>   # adds runtime/, run.sh, run.ps1, README.md; validates
```

## 3. Check before the full render

Render one frame and look at it:
`sh run.sh --preview --time <s>` → `preview.png`. Iterate on the code until it looks
right. A preview is fast locally, so take 2–3 at key moments.

## 4. Render

Run `python3 -I scripts/inspect_pack.py <folder>`, show the user the command and the tools
it found, then run `sh run.sh` as in the main workflow and report the result.

If they want to share the pack, `python3 scripts/build_pack.py build <folder> --out <name>.zip`.
