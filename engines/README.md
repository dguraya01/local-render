# Engines

Each engine is a folder with one `adapter.py` plus an `AUTHORING.md` guide.
`_runtime/` holds the shared code that ships inside every render pack.

| Engine | Good for | Needs |
|---|---|---|
| `html-canvas` | Kinetic type, UI motion, canvas/WebGL, CSS animation | Node 18+, Chrome/Edge/Chromium, ffmpeg |
| `remotion` | React-based motion graphics, data-driven video | Node 18+ |
| `blender` | 3D scenes, product shots, abstract 3D loops | Blender 4.2+, ffmpeg |
| `manim` | Math and explainer animations | Manim Community 0.18+, ffmpeg |
| `ffmpeg` | Slideshows, image sequences, stills + audio | ffmpeg |

## How a pack renders

```
run.sh / run.ps1  →  runtime/lr_render.py  →  runtime/adapter.py (this engine)
                         │                        │
                         ├ validate render.json   ├ render(ctx): produce ctx.out_path
                         ├ check tools            └ preview(ctx, t, out_png, scale)
                         ├ pick encoder (VideoToolbox → NVENC → libx264)
                         └ report size, duration, render time
```

`build_pack.py` (in the render-pack skill) copies `_runtime/*`, the schema, and the
engine's `adapter.py` + `RUNTIME_FILES` into the pack's `runtime/` folder, so a
pack renders on any machine without this repo.

## Adapter interface

```python
ENGINE = "my-engine"                 # must match render.json "engine" and the schema enum
REQUIRES = [{"tool": "ffmpeg", "min_version": "4.4", "why": "..."}]   # defaults for render.json
RUNTIME_FILES = ["helper.js"]        # extra files from this folder copied into runtime/
DEPENDENCIES = {}                    # defaults for render.json "dependencies"
USES_FFMPEG_ENCODER = True           # False if the engine encodes by itself

def engine_command(manifest) -> str: ...      # human-readable command, shown before running
def render(ctx) -> None: ...                  # write the final video to ctx.out_path
def preview(ctx, t, out_png, scale) -> None: ...  # write one low-res frame
```

`ctx` gives you `manifest`, `options` (engine_options), `pack_dir`, `runtime_dir`,
`work_dir` (temporary, deleted afterwards), `out_path`, `total_frames`, `workers`,
`tools` (resolved paths, e.g. `ctx.tools["ffmpeg"]`), `encoder`, `hw`, `path(rel)`
and `npm_install(folder)`.

Helpers in `lr_common`: `stream(cmd, on_line=...)`, `Progress(total)`,
`encode_frames(ctx, "frames/frame_%06d.png")`, `run_ffmpeg(cmd, total_frames)`,
`encoder_args(name, w, h, fps)`.

## Adding an engine

1. Create `engines/<name>/adapter.py` and `engines/<name>/AUTHORING.md`.
2. Add `<name>` to the `engine` enum in `schema/render.schema.json` and to
   `ENGINE_TOOLS` in `_runtime/lr_validate.py`.
3. If it needs a new tool, add it to `TOOLS` in `_runtime/lr_common.py` (with install
   commands) and to the `requires.tool` enum in the schema.
4. Add `examples/<name>/`, run `python3 scripts/build_examples.py`, render it, and run the tests.
