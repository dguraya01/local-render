# Troubleshooting renders

Always quote the actual error to the user. The `--- last output ---` block printed by
`lr_render.py` usually names the cause.

## General

| Symptom | Fix |
|---|---|
| `missing or outdated tools` | Show the printed install command; ask before running it |
| Encoder error (VideoToolbox/NVENC) | Retry with `sh run.sh --encoder libx264` |
| Output length differs from render.json | The animation's real length wins; fix `duration` and re-render if needed |
| Out of memory / machine freezes | `sh run.sh --workers 2` |
| Want to inspect frames | `sh run.sh --keep-work` keeps `.lr-work/` |
| Tool installed but not found | Set the path: `LR_BLENDER=/path/to/blender sh run.sh` (also `LR_FFMPEG`, `LR_NODE`, `LR_MANIM`, `LR_CHROME`) |

## html-canvas

- `Could not start Chrome, Edge or Chromium`: install Chrome, or `cd runtime && npx playwright install chromium`, or set `LR_CHROME`.
- Blank or frozen frames: the page doesn't define `window.renderFrame(t)` and uses
  `requestAnimationFrame`/timers. Make drawing a function of `t` (see the engine guide).
- `page error:` lines are JavaScript exceptions from the pack's page. Fix the source.

## remotion

- First run downloads npm packages and a headless browser; it needs internet once.
- `Could not find composition`: `engine_options.composition` must match a `<Composition id>`.
- Version mismatch warnings: all `remotion` and `@remotion/*` packages must share one version.

## blender

- `blender` not found: Blender is searched on PATH, then `/Applications/Blender.app`,
  `C:\Program Files\Blender Foundation\Blender *`, `/snap/bin/blender`. Otherwise set `LR_BLENDER`.
- Python traceback from `scene.py`: an API difference between Blender versions. The guide
  lists the safe APIs (drivers instead of `action.fcurves`, `"Emission Color"`).
- Too slow: switch `engine_options.render_engine` to `eevee` or lower `samples`.

## manim

- `manim` not found: `uv tool install manim --python 3.12` (or `pipx install manim`).
  macOS may first need `brew install pkg-config cairo pango`.
- `LaTeX` errors: the scene uses `MathTex`/`Tex`. Install a TeX distribution (MacTeX,
  MiKTeX, `texlive`), or replace those mobjects with `Text`.

## ffmpeg

- `No such filter: 'xfade'` or `'zoompan'`: ffmpeg is older than 4.3; upgrade it.
- Wrong length: slide durations minus transitions must add up to `duration`.
