"""remotion engine: render a React/Remotion project with the Remotion CLI.

The Remotion project lives in the pack's src/ folder (src/package.json,
src/index.ts calling registerRoot). render.json's resolution/fps/duration are
passed in as props.lr so the composition can adopt them via calculateMetadata.
"""
import json
import os
import re

import lr_common as C

ENGINE = "remotion"
REQUIRES = [
    {"tool": "node", "min_version": "18", "why": "runs the Remotion CLI"},
    {"tool": "npm", "min_version": "8", "why": "installs Remotion into src/node_modules"},
]
RUNTIME_FILES = []
DEPENDENCIES = {"npm": {"remotion": "4.0.541", "@remotion/cli": "4.0.541", "react": "19.2.0",
                        "react-dom": "19.2.0"}, "npm_dir": "src"}
# Remotion bundles its own ffmpeg; we pass it the hardware-acceleration flag instead.
USES_FFMPEG_ENCODER = False


def _project(m):
    return (m.get("dependencies") or {}).get("npm_dir", "src")


def _entry(m):
    return os.path.relpath(m["entry"], _project(m)).replace(os.sep, "/")


def _comp(m):
    return (m.get("engine_options") or {}).get("composition", "Main")


def engine_command(m):
    return ("cd %s && npx remotion render %s %s ../%s --codec=%s --props='{\"lr\":{...}}' "
            "--hardware-acceleration=if-possible"
            % (_project(m), _entry(m), _comp(m), m["output"], "h265" if m.get("codec") == "hevc" else "h264"))


def _props(ctx):
    m = ctx.manifest
    props = dict(ctx.options.get("props") or {})
    props["lr"] = {"width": m["resolution"]["width"], "height": m["resolution"]["height"],
                   "fps": m["fps"], "durationInFrames": ctx.total_frames}
    return json.dumps(props)


def _npx(ctx):
    npm = ctx.tools.get("npm") or C.find_tool("npm")
    npx = os.path.join(os.path.dirname(npm), "npx.cmd" if C.os_key() == "windows" else "npx")
    return npx if os.path.exists(npx) else "npx"


def render(ctx):
    m = ctx.manifest
    proj = ctx.path(_project(m))
    ctx.npm_install(proj)
    codec = "h265" if m.get("codec") == "hevc" else "h264"
    cmd = [_npx(ctx), "remotion", "render", _entry(m), _comp(m), ctx.out_path,
           "--codec=" + codec, "--props=" + _props(ctx), "--log=info"]
    if ctx.hw["apple_silicon"]:
        cmd.append("--hardware-acceleration=if-possible")
        C.log("encoder: Remotion + VideoToolbox (hardware acceleration if possible)")
    else:
        cmd += ["--x264-preset=fast"] if codec == "h264" else []
        C.log("encoder: Remotion built-in %s" % codec)
    if ctx.args.workers:
        cmd.append("--concurrency=%d" % ctx.args.workers)
    prog = C.Progress(ctx.total_frames, "frames rendered")

    def on_line(line):
        # Remotion prints e.g. "Rendered 120/180" and "Encoded 120/180"
        low = line.lower()
        if low.startswith("rendered ") or low.startswith("rendering frames"):
            mt = re.search(r"(\d+)/(\d+)", line)
            if mt:
                prog.update(int(mt.group(1)))
            return False
        if low.startswith(("encoded ", "encoding ", "stitching", "getting composition", "bundling", "bundled")):
            return False
        return True

    C.stream(cmd, cwd=proj, on_line=on_line)


def preview(ctx, t, out_png, scale):
    m = ctx.manifest
    proj = ctx.path(_project(m))
    ctx.npm_install(proj)
    frame = min(ctx.total_frames - 1, int(round(t * m["fps"])))
    C.stream([_npx(ctx), "remotion", "still", _entry(m), _comp(m), out_png, "--frame=%d" % frame,
              "--scale=%s" % scale, "--props=" + _props(ctx)], cwd=proj)
