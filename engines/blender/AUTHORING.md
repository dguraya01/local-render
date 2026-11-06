# blender: authoring guide

Best for 3D: product shots, abstract loops, logo reveals, scenes with real lighting.
Blender runs headless (`blender -b --factory-startup -P`), renders PNG frames on the GPU,
and ffmpeg encodes them with the fastest encoder.

## Files

```
render.json      entry: "src/scene.py"
src/scene.py     builds the scene with bpy. It must NOT render or set the output path.
assets/          textures, HDRIs, .glb/.obj models (load with paths relative to src/)
```

The driver (`runtime/blender_driver.py`) execs `scene.py` with the working directory set to
`src/`, then applies render.json: resolution, fps, frame range `1..fps*duration`, render
engine, GPU devices, PNG output. These globals are available inside `scene.py`:
`LR_FPS`, `LR_FRAMES`, `LR_WIDTH`, `LR_HEIGHT`.

## Skeleton

```python
import math, bpy
FRAMES = globals().get("LR_FRAMES", 120)
for obj in list(bpy.data.objects):          # factory startup has a cube, light, camera
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene

bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
ball = bpy.context.object
fc = ball.driver_add("location", 2)          # animate with a driver expression of `frame`
fc.driver.expression = "0.3*sin(frame*%.5f)" % (math.tau / FRAMES)

bpy.ops.object.camera_add(location=(0, -8, 2), rotation=(math.radians(80), 0, 0))
scene.camera = bpy.context.object
bpy.ops.object.light_add(type="AREA", location=(3, -3, 5))
```

## Rules

- **Animate with drivers** (simple expressions of `frame`, `sin`, `cos`, `pi`) or with
  `obj.keyframe_insert(...)`. Avoid `action.fcurves`: that API changed in Blender 4.4/5.0.
  Simple driver expressions run with `--factory-startup` (no Python auto-exec needed).
- Make loops seamless: rotate whole turns over `FRAMES`.
- Always set `scene.camera`, add lights or a world, and delete the default objects.
- Use the Principled BSDF; for emission use input `"Emission Color"` (4.x/5.x) and fall
  back to `"Emission"` for older versions.
- Keep geometry procedural or bundle models in `assets/`. No network access.

## engine_options

| key | default | meaning |
|---|---|---|
| `render_engine` | `"eevee"` | `"eevee"` (fast, GPU), `"cycles"` (path traced, Metal/OptiX/CUDA), `"workbench"` |
| `samples` | engine default | Eevee TAA samples or Cycles samples (16–64 Eevee, 64–256 Cycles) |

Rough cost on an M-series laptop at 1080p: Eevee 1–2 s/frame, Cycles 5–30 s/frame.
Prefer Eevee unless the user asks for path tracing.

## Preview inside the sandbox

Blender is rarely installed in a sandbox. Skip the preview rather than installing it.
