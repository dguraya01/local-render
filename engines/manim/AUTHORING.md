# manim: authoring guide

Best for math and explainer animations: graphs, equations, geometry, step-by-step diagrams.
Uses Manim Community (`manim`). The scene renders to manim's own mp4, then ffmpeg
re-encodes it with the fastest encoder and adds audio.

## Files

```
render.json      entry: "src/scene.py", engine_options.scene: "Main"
src/scene.py     a Scene subclass named in engine_options.scene
assets/          images/SVGs (ImageMobject / SVGMobject paths relative to src/)
```

## Skeleton

```python
from manim import *

config.background_color = "#0b0d17"
Text.set_default(font="Helvetica Neue")     # falls back to a system sans if missing

class Main(Scene):
    def construct(self):
        title = Text("Hello", font_size=64)
        self.play(Write(title), run_time=1)
        self.wait(1)
```

## Rules

- **No LaTeX by default.** `MathTex`, `Tex` and `Axes(include_numbers=True)` need a LaTeX
  install, which most users lack. Use `Text`/`MarkupText` and place tick labels yourself.
  If the user explicitly wants LaTeX, add a note to the pack README and say so.
- The video's length is the sum of `run_time`s and `wait`s. Set render.json `duration` to
  match; if it differs, the renderer uses the scene's real length and prints a note.
- Resolution and fps come from render.json (`-r W,H --fps F`); don't set them in code.
- `always_redraw` / `ValueTracker` are fine; avoid wall-clock time and unseeded randomness.

## engine_options

| key | default | meaning |
|---|---|---|
| `scene` | `"Main"` | Scene class to render |

## Preview inside the sandbox

If `manim` is importable, `build_pack.py preview` saves the last frame at low resolution.
Otherwise skip it; `pip install manim` needs system Cairo/Pango and is slow.
