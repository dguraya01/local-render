"""html-canvas engine: capture an HTML/CSS/JS animation frame by frame in
headless Chrome (Playwright), then encode with ffmpeg."""
import os

import lr_common as C

ENGINE = "html-canvas"
REQUIRES = [
    {"tool": "node", "min_version": "18", "why": "runs the Playwright frame capture"},
    {"tool": "npm", "min_version": "8", "why": "installs playwright-core into runtime/"},
    {"tool": "chrome", "why": "headless browser that draws the frames (Chrome, Edge or Chromium)"},
    {"tool": "ffmpeg", "min_version": "4.4", "why": "encodes the frames to video"},
]
RUNTIME_FILES = ["capture.mjs", "package.json"]
DEPENDENCIES = {"npm": {"playwright-core": "1.65.0"}, "npm_dir": "runtime"}
USES_FFMPEG_ENCODER = True


def engine_command(m):
    return ("node runtime/capture.mjs --entry %s --width %d --height %d --fps %s --frames %d "
            "&& ffmpeg -i .lr-work/frames/frame_%%06d.png <fastest encoder> %s"
            % (m["entry"], m["resolution"]["width"], m["resolution"]["height"], m["fps"],
               round(m["fps"] * m["duration"]), m["output"]))


def _base_cmd(ctx):
    m = ctx.manifest
    cmd = [ctx.tools["node"], os.path.join(ctx.runtime_dir, "capture.mjs"),
           "--root", ctx.pack_dir, "--entry", m["entry"],
           "--width", str(m["resolution"]["width"]), "--height", str(m["resolution"]["height"]),
           "--fps", str(m["fps"])]
    return cmd


def _env(ctx):
    env = dict(os.environ)
    chrome = ctx.tools.get("chrome")
    if chrome and "LR_CHROME" not in env:
        env["LR_CHROME"] = chrome
    return env


def render(ctx):
    ctx.npm_install(ctx.runtime_dir)
    frames = os.path.join(ctx.work_dir, "frames")
    fmt = ctx.options.get("frame_format", "png")
    cmd = _base_cmd(ctx) + ["--frames", str(ctx.total_frames), "--out", frames,
                            "--workers", str(ctx.workers), "--format", fmt]
    C.log("capturing %d frames with %d browser workers" % (ctx.total_frames, ctx.workers))
    prog = C.Progress(ctx.total_frames, "frames captured")

    def on_line(line):
        if line.startswith("PROGRESS "):
            prog.update(int(line.split()[1]))
            return False
        return True

    C.stream(cmd, env=_env(ctx), on_line=on_line)
    C.encode_frames(ctx, os.path.join(frames, "frame_%06d." + fmt))


def preview(ctx, t, out_png, scale):
    ctx.npm_install(ctx.runtime_dir)
    C.stream(_base_cmd(ctx) + ["--single", str(t), "--scale", str(scale), "--png", out_png], env=_env(ctx))
