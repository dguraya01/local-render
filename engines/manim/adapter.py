"""manim engine: render a Manim Community scene, then re-encode it with the
fastest available ffmpeg encoder (and mux render.json audio)."""
import glob
import os

import lr_common as C

ENGINE = "manim"
REQUIRES = [
    {"tool": "manim", "min_version": "0.18", "why": "draws the math animation (Manim Community)"},
    {"tool": "ffmpeg", "min_version": "4.4", "why": "encodes the frames with the fastest encoder"},
]
RUNTIME_FILES = []
DEPENDENCIES = {"pip": {"manim": ">=0.18"}}
USES_FFMPEG_ENCODER = True


def _scene(m):
    return (m.get("engine_options") or {}).get("scene", "Main")


def engine_command(m):
    return ("manim render %s %s --format mp4 -r %d,%d --fps %s --media_dir .lr-work/media --disable_caching "
            "&& ffmpeg -i .lr-work/media/videos/.../%s.mp4 <fastest encoder> %s"
            % (m["entry"], _scene(m), m["resolution"]["width"], m["resolution"]["height"], m["fps"], _scene(m),
               m["output"]))


def _cmd(ctx, w, h, extra):
    m = ctx.manifest
    return [ctx.tools["manim"], "render", ctx.path(m["entry"]), _scene(m),
            "-r", "%d,%d" % (w, h), "--fps", str(m["fps"]),
            "--media_dir", os.path.join(ctx.work_dir, "media"), "--disable_caching",
            "--progress_bar", "none", "-v", "WARNING"] + extra


def _env():
    env = dict(os.environ)
    env["PYTHONWARNINGS"] = "ignore"  # silence third-party SyntaxWarnings (pydub)
    return env


def render(ctx):
    m = ctx.manifest
    w, h = m["resolution"]["width"], m["resolution"]["height"]
    C.log("rendering scene %s with manim (%d frames expected)" % (_scene(m), ctx.total_frames))
    # manim's own mp4 is the intermediate: its png-sequence mode drops the frozen frames of
    # self.wait(), so timing would be wrong. We then re-encode with the fastest encoder.
    C.stream(_cmd(ctx, w, h, ["--format", "mp4"]), env=_env())
    vids = glob.glob(os.path.join(ctx.work_dir, "media", "videos", "**", _scene(m) + ".mp4"), recursive=True)
    if not vids:
        raise RuntimeError("manim produced no video")
    src = max(vids, key=os.path.getmtime)
    info = C.probe(src)
    if info.get("duration"):
        C.log("manim scene length: %.2fs" % info["duration"])
        if abs(info["duration"] - m["duration"]) > 0.05:
            C.log("note: scene is %.2fs but render.json says %ss; using the scene length"
                  % (info["duration"], m["duration"]))
            m["duration"] = round(info["duration"], 3)
            ctx.total_frames = int(round(m["duration"] * m["fps"]))
    C.encode_video(ctx, src)


def preview(ctx, t, out_png, scale):
    m = ctx.manifest
    w = max(16, int(m["resolution"]["width"] * scale))
    h = max(16, int(m["resolution"]["height"] * scale))
    C.stream(_cmd(ctx, w, h, ["-s"]), env=_env())  # -s saves the last frame
    pngs = glob.glob(os.path.join(ctx.work_dir, "media", "images", "**", "*.png"), recursive=True)
    if not pngs:
        raise RuntimeError("manim produced no preview frame")
    os.replace(max(pngs, key=os.path.getmtime), out_png)
