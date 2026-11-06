"""Render this pack on the local machine.

Called by run.sh / run.ps1. Usage (from the pack folder):

    python3 runtime/lr_render.py              # full render
    python3 runtime/lr_render.py --check      # check tools + show the plan, render nothing
    python3 runtime/lr_render.py --preview    # one low-res frame -> preview.png
        [--time SECONDS] [--scale 0.25]
    python3 runtime/lr_render.py --encoder libx264   # force an encoder
    python3 runtime/lr_render.py --workers 4         # parallelism where the engine supports it
    python3 runtime/lr_render.py --keep-work         # keep intermediate frames in .lr-work/
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import time

RUNTIME = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RUNTIME)

import lr_common as C  # noqa: E402
import lr_validate  # noqa: E402


class Context:
    def __init__(self, pack_dir, manifest, args, hw):
        self.pack_dir = pack_dir
        self.runtime_dir = RUNTIME
        self.manifest = manifest
        self.args = args
        self.hw = hw
        self.options = manifest.get("engine_options") or {}
        self.work_dir = os.path.join(pack_dir, ".lr-work")
        self.out_path = os.path.abspath(args.out or os.path.join(pack_dir, manifest["output"]))
        self.total_frames = int(round(manifest["fps"] * manifest["duration"]))
        self.tools = {}
        self.encoder = None
        cpus = hw["cpu_count"]
        self.workers = args.workers or max(1, min(8, cpus // 2 if cpus > 2 else 1))

    def path(self, rel):
        return os.path.join(self.pack_dir, rel)

    def log(self, msg=""):
        C.log(msg)

    def npm_install(self, folder):
        """Install npm deps into folder/node_modules if they are not there yet."""
        if os.path.isdir(os.path.join(folder, "node_modules")):
            return
        npm = C.find_tool("npm")
        if not npm:
            raise RuntimeError("npm is required. Install Node.js: " + C.TOOLS["npm"]["install"][C.os_key()])
        lock = os.path.exists(os.path.join(folder, "package-lock.json"))
        C.log("installing npm packages into %s (first run only)" % os.path.relpath(folder, self.pack_dir))
        C.stream([npm, "ci" if lock else "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=folder)


def load_adapter():
    spec = importlib.util.spec_from_file_location("lr_adapter", os.path.join(RUNTIME, "adapter.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(description="Render this local-render pack.")
    ap.add_argument("--check", action="store_true", help="check tools and print the plan only")
    ap.add_argument("--preview", action="store_true", help="render one low-res frame to preview.png")
    ap.add_argument("--time", type=float, default=None, help="preview time in seconds")
    ap.add_argument("--scale", type=float, default=0.25, help="preview scale (default 0.25)")
    ap.add_argument("--encoder", help="force an ffmpeg encoder, e.g. libx264")
    ap.add_argument("--workers", type=int, help="parallel workers")
    ap.add_argument("--out", help="output path (default: manifest output next to render.json)")
    ap.add_argument("--keep-work", action="store_true", help="keep .lr-work/ intermediates")
    args = ap.parse_args()

    pack_dir = os.path.dirname(RUNTIME)
    manifest, errs = lr_validate.validate_pack(pack_dir)
    if errs:
        C.log("render.json is not valid:")
        for e in errs:
            print("    - " + e)
        return 2

    hw = C.detect_hardware()
    C.log("%s  |  engine: %s  |  %dx%d @ %sfps, %ss"
          % (manifest["title"], manifest["engine"], manifest["resolution"]["width"],
             manifest["resolution"]["height"], manifest["fps"], manifest["duration"]))
    gpu = "Apple Silicon" if hw["apple_silicon"] else (hw["nvidia_gpu"] or "no supported GPU")
    C.log("machine: %s, %d cores, %s (%s)" % (hw["cpu"], hw["cpu_count"], gpu, hw["os"]))

    adapter = load_adapter()
    ctx = Context(pack_dir, manifest, args, hw)

    results = C.check_requirements(manifest["requires"])
    bad = [r for r in results if r["status"] != "ok"]
    for r in results:
        C.log("  %-8s %-8s %s" % (r["tool"], r["status"], r["version"] or ""))
    if bad:
        C.log("missing or outdated tools. Install, then run again:")
        for r in bad:
            need = (" (need >= %s, found %s)" % (r["min_version"], r["version"])) if r["status"] == "too_old" else ""
            print("    %s%s:  %s" % (r["tool"], need, r["install"]))
        return 3
    ctx.tools = {r["tool"]: r["path"] for r in results}
    for t in ("ffmpeg", "ffprobe"):
        ctx.tools.setdefault(t, C.find_tool(t))

    if ctx.tools.get("ffmpeg") and getattr(adapter, "USES_FFMPEG_ENCODER", True):
        ctx.encoder = C.pick_encoder(ctx.tools["ffmpeg"], manifest.get("codec", "h264"), hw, args.encoder)
        C.log("encoder: %s" % ctx.encoder)
    C.log("engine command: %s" % manifest["render"]["engine_command"])

    if args.check:
        C.log("check passed. Run without --check to render.")
        return 0

    os.makedirs(ctx.work_dir, exist_ok=True)
    t0 = time.time()
    try:
        if args.preview:
            out_png = os.path.join(pack_dir, "preview.png")
            t = args.time if args.time is not None else manifest["duration"] / 2
            adapter.preview(ctx, t, out_png, args.scale)
            C.log("preview written: %s (%.1fs)" % (out_png, time.time() - t0))
            return 0
        if os.path.exists(ctx.out_path):
            os.remove(ctx.out_path)
        adapter.render(ctx)
    finally:
        if not args.keep_work:
            shutil.rmtree(ctx.work_dir, ignore_errors=True)
    elapsed = time.time() - t0

    if not os.path.isfile(ctx.out_path):
        C.log("render finished but no output was produced at %s" % ctx.out_path)
        return 4
    info = C.probe(ctx.out_path)
    size = os.path.getsize(ctx.out_path)
    report = {
        "output": ctx.out_path, "size_bytes": size, "size": C.human_size(size),
        "duration_s": round(info.get("duration", 0), 3), "width": info.get("width"),
        "height": info.get("height"), "video_codec": info.get("codec"), "audio_codec": info.get("audio"),
        "encoder": ctx.encoder, "engine": manifest["engine"], "render_seconds": round(elapsed, 2),
        "machine": {"cpu": hw["cpu"], "cores": hw["cpu_count"], "apple_silicon": hw["apple_silicon"],
                    "nvidia_gpu": hw["nvidia_gpu"]},
    }
    with open(os.path.join(pack_dir, "render-report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print()
    C.log("DONE")
    C.log("  output:      %s" % ctx.out_path)
    C.log("  size:        %s" % report["size"])
    C.log("  duration:    %.2fs  (%sx%s, %s%s)" % (report["duration_s"], report["width"], report["height"],
                                                    report["video_codec"],
                                                    ", audio " + report["audio_codec"] if report["audio_codec"] else ""))
    C.log("  render time: %s" % C.fmt_secs(elapsed) if elapsed >= 10 else "  render time: %.1fs" % elapsed)
    expected = manifest["duration"]
    if info.get("duration") and abs(info["duration"] - expected) > max(0.5, expected * 0.05):
        C.log("  note: output is %.2fs but render.json says %ss" % (info["duration"], expected))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        C.log("cancelled")
        sys.exit(130)
    except RuntimeError as e:
        C.log("ERROR: %s" % e)
        sys.exit(1)
