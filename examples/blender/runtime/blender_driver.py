"""Runs inside Blender:  blender -b --factory-startup -P blender_driver.py -- [options]

1. exec()s the pack's scene script (which only BUILDS the scene; it never renders)
2. applies render.json settings: resolution, fps, frame range, render engine, GPU
3. renders a PNG sequence (or one still for --single)

Options after `--`:
  --scene PATH --out DIR --width W --height H --fps F --frames N
  [--engine eevee|cycles|workbench] [--samples S] [--single FRAME --scale 0.25 --png OUT]
"""
import argparse
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--scene", required=True)
ap.add_argument("--out")
ap.add_argument("--width", type=int, required=True)
ap.add_argument("--height", type=int, required=True)
ap.add_argument("--fps", type=float, required=True)
ap.add_argument("--frames", type=int, required=True)
ap.add_argument("--engine", default="eevee")
ap.add_argument("--samples", type=int, default=0)
ap.add_argument("--single", type=int)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--png")
a = ap.parse_args(argv)

scene_path = os.path.abspath(a.scene)
os.chdir(os.path.dirname(scene_path))  # relative asset paths resolve from the script folder
g = {"__name__": "__main__", "__file__": scene_path, "LR_FPS": a.fps, "LR_FRAMES": a.frames,
     "LR_WIDTH": a.width, "LR_HEIGHT": a.height}
with open(scene_path, encoding="utf-8") as f:
    exec(compile(f.read(), scene_path, "exec"), g)

sc = bpy.context.scene
r = sc.render
r.resolution_x, r.resolution_y = a.width, a.height
r.resolution_percentage = max(1, int(round(a.scale * 100)))
fps_int = int(round(a.fps))
r.fps, r.fps_base = fps_int, fps_int / a.fps
sc.frame_start, sc.frame_end = 1, a.frames


def set_engine(kind):
    if kind == "cycles":
        r.engine = "CYCLES"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = backend
                prefs.get_devices()
                gpus = [d for d in prefs.devices if d.type != "CPU"]
                if gpus:
                    for d in prefs.devices:
                        d.use = True
                    sc.cycles.device = "GPU"
                    print("LR: Cycles on %s (%s)" % (backend, ", ".join(d.name for d in gpus)))
                    break
            except (TypeError, ValueError):
                continue
        if a.samples:
            sc.cycles.samples = a.samples
        sc.cycles.use_denoising = True
        return
    if kind == "workbench":
        r.engine = "BLENDER_WORKBENCH"
        return
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):  # 4.2-4.x vs 5.x naming
        try:
            r.engine = name
            break
        except TypeError:
            continue
    if a.samples:
        sc.eevee.taa_render_samples = a.samples


set_engine(a.engine)
print("LR: engine %s, %dx%d @ %d%%, %s fps, %d frames" % (r.engine, a.width, a.height,
                                                          r.resolution_percentage, a.fps, a.frames))

r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.use_file_extension = True

if a.single is not None:
    sc.frame_set(max(1, min(a.frames, a.single)))
    r.filepath = os.path.abspath(a.png)
    bpy.ops.render.render(write_still=True)
else:
    os.makedirs(a.out, exist_ok=True)
    r.filepath = os.path.join(os.path.abspath(a.out), "frame_######")
    bpy.ops.render.render(animation=True)
