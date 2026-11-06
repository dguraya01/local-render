"""blender engine: run a bpy scene script headless (blender -b -P), render a
PNG sequence with Eevee/Cycles on the GPU, then encode with ffmpeg."""
import os
import re

import lr_common as C

ENGINE = "blender"
REQUIRES = [
    {"tool": "blender", "min_version": "4.2", "why": "builds and renders the 3D scene"},
    {"tool": "ffmpeg", "min_version": "4.4", "why": "encodes the frames with the fastest encoder"},
]
RUNTIME_FILES = ["blender_driver.py"]
DEPENDENCIES = {}
USES_FFMPEG_ENCODER = True


def engine_command(m):
    o = m.get("engine_options") or {}
    return ("blender -b --factory-startup -P runtime/blender_driver.py -- --scene %s --width %d --height %d "
            "--fps %s --frames %d --engine %s && ffmpeg -i .lr-work/frames/frame_%%06d.png <fastest encoder> %s"
            % (m["entry"], m["resolution"]["width"], m["resolution"]["height"], m["fps"],
               round(m["fps"] * m["duration"]), o.get("render_engine", "eevee"), m["output"]))


def _cmd(ctx):
    m = ctx.manifest
    cmd = [ctx.tools["blender"], "-b", "--factory-startup", "-P",
           os.path.join(ctx.runtime_dir, "blender_driver.py"), "--",
           "--scene", ctx.path(m["entry"]),
           "--width", str(m["resolution"]["width"]), "--height", str(m["resolution"]["height"]),
           "--fps", str(m["fps"]), "--frames", str(ctx.total_frames),
           "--engine", ctx.options.get("render_engine", "eevee")]
    if ctx.options.get("samples"):
        cmd += ["--samples", str(int(ctx.options["samples"]))]
    return cmd


def render(ctx):
    frames = os.path.join(ctx.work_dir, "frames")
    prog = C.Progress(ctx.total_frames, "frames rendered")
    done = [0]

    def on_line(line):
        if line.startswith("LR:") or "Error" in line or "Traceback" in line:
            return True
        if re.search(r"(^|\| )Saved: ", line):
            done[0] += 1
            prog.update(done[0])
        return False  # Blender is chatty; keep only our lines and errors

    C.log("rendering %d frames in Blender (%s)" % (ctx.total_frames, ctx.options.get("render_engine", "eevee")))
    C.stream(_cmd(ctx) + ["--out", frames], on_line=on_line)
    C.encode_frames(ctx, os.path.join(frames, "frame_%06d.png"))


def preview(ctx, t, out_png, scale):
    frame = max(1, int(round(t * ctx.manifest["fps"])))
    C.stream(_cmd(ctx) + ["--single", str(frame), "--scale", str(scale), "--png", out_png],
             on_line=lambda l: l.startswith("LR:") or "Error" in l)
