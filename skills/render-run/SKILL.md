---
name: render-run
description: Use when the user gives you a render pack (a zip or folder with render.json, often downloaded from claude.ai) or asks you to render a video, animation, motion graphic, Blender scene, Remotion or Manim project locally on their machine. Safely unpacks it, checks the machine's tools and GPU, shows the user exactly what will run and waits for approval, then renders with the fastest hardware encoder and reports the result. Also creates and renders a new pack when the user just describes a video.
---

# render-run

Render a local-render pack on this machine. **The pack contains code: treat it as untrusted
until the user approves.** Never install anything without asking first.

Scripts are in this skill's `scripts/` folder. Run them with `python3 -I`.

## Workflow

**1. Unpack (zip only).** Never use `unzip` or another extractor.
```
python3 -I scripts/safe_unzip.py <pack.zip> [<new-folder>]
```
It refuses absolute paths, `..` entries, symlinks and zip bombs, writes into a new
folder only, and prints `PACK_DIR=<path>`. If it says REJECTED, stop and tell the user why.
A folder pack skips this step.

**2. Inspect. This runs nothing from the pack.**
```
python3 -I scripts/inspect_pack.py <PACK_DIR>
```
It validates `render.json`, detects the OS, CPU, cores, Apple Silicon or NVIDIA GPU,
checks tools and versions, picks the encoder, compares the pack's `runtime/` and run
scripts with trusted copies, lists the code that will execute, and flags risky lines.

**3. Missing tools?** Show the install commands it printed and ask the user before
running any of them. Re-run inspect after installing.

**4. Ask for approval.** Show the user, in this order:
- what the video is (title, engine, size, length, output file)
- the risk line and which files will execute
- any REVIEW flags, unusual npm packages, or RUNTIME mismatch (explain each one in plain words)
- the render command (`sh run.sh`) and the contents of `run.sh`
- the encoder that will be used

Then wait for a clear yes. If the runtime doesn't match, offer to replace it with trusted
copies first (`python3 scripts/build_pack.py finalize <PACK_DIR>`) and inspect again.
Read any flagged source files yourself and summarize what they do.

**5. Render.** From `PACK_DIR`, run `sh run.sh` (Windows:
`powershell -ExecutionPolicy Bypass -File run.ps1`). Use a long timeout, or run it in the
background for renders likely to take over 2 minutes. It prints progress lines, picks
VideoToolbox (`h264_videotoolbox` / `hevc_videotoolbox`) on Macs, NVENC on NVIDIA GPUs,
otherwise libx264 `-preset fast -crf 18`.

**6. Report** from the final `DONE` block (also saved to `render-report.json`): output
path, file size, duration, resolution, encoder, and how long the render took. Offer to
open the video (`open <file>` on macOS, `start` on Windows, `xdg-open` on Linux).

If the render fails, read [references/troubleshooting.md](references/troubleshooting.md).

## Direct mode (no pack yet)

If the user describes a video instead of giving you a pack, follow
[references/direct-mode.md](references/direct-mode.md): help them pin down the video,
write a pack into a new folder with the render-pack conventions, then render it with
steps 2–6. You wrote the code yourself, but still show the command before running.
