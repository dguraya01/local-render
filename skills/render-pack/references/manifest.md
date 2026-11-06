# render.json reference

Full JSON Schema: `schema/render.schema.json` (copied into every pack as
`runtime/render.schema.json`). You write the fields marked **you**; `build_pack.py
finalize/build` fills the rest.

| Field | Who | Notes |
|---|---|---|
| `schema_version` | auto | `"1.0"` |
| `title` | **you** | Shown in the README and run scripts |
| `description` | **you** | One or two sentences, optional |
| `engine` | **you** | `html-canvas`, `remotion`, `blender`, `manim`, `ffmpeg` |
| `entry` | **you** | Main file, relative path, e.g. `src/index.html` |
| `output` | **you** | File name only, `.mp4` or `.mov`, e.g. `launch-teaser.mp4` |
| `resolution` | **you** | `{ "width": 1920, "height": 1080 }`. Vertical: 1080x1920. Square: 1080x1080 |
| `fps` | **you** | 24, 25, 30 or 60 |
| `duration` | **you** | Seconds. Must match the animation's real length |
| `codec` | optional | `h264` (default, plays everywhere) or `hevc` (smaller files) |
| `audio` | optional | Relative path to an audio file in `assets/`; muxed in and faded out |
| `requires` | auto | Tools + minimum versions: `[{ "tool": "ffmpeg", "min_version": "4.4" }]` |
| `dependencies` | auto/**you** | `npm_dir` + `npm` (read from that folder's package.json), `pip` (informational) |
| `render.command` | auto | `sh run.sh` |
| `render.windows_command` | auto | `powershell -ExecutionPolicy Bypass -File run.ps1` |
| `render.engine_command` | auto | The underlying engine invocation, for transparency |
| `engine_options` | **you** | Engine-specific; see the engine's guide |
| `generator` | auto | `{ "name": "local-render", "version": "..." }` |

Paths are relative, use forward slashes, and may not start with `/`, contain a drive letter,
backslashes or `..`. Symlinks are not allowed in a pack.

## Pack layout

```
render.json     manifest
src/            source code
assets/         images, fonts, audio
runtime/        local-render renderer (added by build_pack.py; don't edit)
run.sh          macOS/Linux one-command render
run.ps1         Windows one-command render
README.md       plain-language instructions (generated unless you write your own)
preview.png     optional single test frame
```

`run.sh` and `run.ps1` only find Python 3.8+ and run `runtime/lr_render.py`, which
validates the manifest, checks tools, picks the fastest encoder (VideoToolbox, then NVENC,
then libx264), renders with progress output and prints the output path, size, duration and
render time. Flags: `--check`, `--preview [--time S] [--scale 0.25]`, `--encoder NAME`,
`--workers N`, `--keep-work`.
