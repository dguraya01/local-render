"""ffmpeg engine: slideshows (stills with Ken Burns motion and transitions),
image sequences, and stills + audio, built from a JSON description.

entry (e.g. src/slideshow.json) is either:
  {"slides": [{"image": "assets/a.png", "duration": 3}, ...],
   "transition": {"type": "fade", "duration": 0.8},       # any ffmpeg xfade transition
   "ken_burns": {"zoom": 1.08}}                             # or false
or:
  {"sequence": {"pattern": "assets/frames/f_%04d.png", "start_number": 1}}
Audio comes from render.json "audio".
"""
import json
import os

import lr_common as C

ENGINE = "ffmpeg"
REQUIRES = [{"tool": "ffmpeg", "min_version": "4.4", "why": "builds and encodes the whole video"}]
RUNTIME_FILES = []
DEPENDENCIES = {}
USES_FFMPEG_ENCODER = True


def engine_command(m):
    return ("ffmpeg -loop 1 -i <each slide> ... -filter_complex '<scale, zoompan, xfade chain>' "
            "<fastest encoder> %s   (graph built from %s)" % (m["output"], m["entry"]))


def load_spec(ctx):
    with open(ctx.path(ctx.manifest["entry"]), encoding="utf-8") as f:
        return json.load(f)


def slides_length(spec):
    slides = spec["slides"]
    td = float((spec.get("transition") or {}).get("duration", 0)) if len(slides) > 1 else 0
    return sum(float(s["duration"]) for s in slides) - td * (len(slides) - 1)


def build(ctx, spec, scale=1.0):
    """Return (input_args, filtergraph, video_label, total_seconds)."""
    m = ctx.manifest
    W, H, fps = m["resolution"]["width"], m["resolution"]["height"], m["fps"]
    ow, oh = int(W * scale) // 2 * 2, int(H * scale) // 2 * 2
    inputs, chains = [], []
    if "sequence" in spec:
        seq = spec["sequence"]
        inputs += ["-framerate", str(fps), "-start_number", str(seq.get("start_number", 1)),
                   "-i", ctx.path(seq["pattern"])]
        chains.append("[0:v]scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,"
                      "setsar=1,format=yuv420p[vout]" % (ow, oh, ow, oh))
        return inputs, ";".join(chains), "[vout]", m["duration"]

    slides = spec["slides"]
    trans = spec.get("transition") or {}
    ttype, td = trans.get("type", "fade"), float(trans.get("duration", 0.8))
    kb = spec.get("ken_burns", {"zoom": 1.08})
    zoom = float(kb.get("zoom", 1.08)) if kb else 1.0
    for i, s in enumerate(slides):
        d = float(s["duration"])
        nframes = max(1, int(round(d * fps)))
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", "%.3f" % d, "-i", ctx.path(s["image"])]
        if zoom > 1.0:
            z = ("1+%.5f*on/%d" % (zoom - 1, nframes)) if i % 2 == 0 else ("%.5f-%.5f*on/%d" % (zoom, zoom - 1, nframes))
            chains.append(
                "[%d:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
                "zoompan=z='%s':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=%dx%d:fps=%s,"
                "setsar=1,format=yuv420p[v%d]" % (i, ow * 2, oh * 2, ow * 2, oh * 2, z, ow, oh, fps, i))
        else:
            chains.append("[%d:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%s,"
                          "setsar=1,format=yuv420p[v%d]" % (i, ow, oh, ow, oh, fps, i))
    label, t = "[v0]", float(slides[0]["duration"])
    for i in range(1, len(slides)):
        offset = t - td
        chains.append("%s[v%d]xfade=transition=%s:duration=%.3f:offset=%.3f[x%d]" % (label, i, ttype, td, offset, i))
        label, t = "[x%d]" % i, offset + float(slides[i]["duration"])
    return inputs, ";".join(chains), label, t


def render(ctx):
    m = ctx.manifest
    spec = load_spec(ctx)
    inputs, graph, vlabel, total = build(ctx, spec)
    if "slides" in spec and abs(total - m["duration"]) > 0.05:
        C.log("note: slides add up to %.2fs; render.json says %ss. Using %.2fs." % (total, m["duration"], total))
    cmd = C.ffmpeg_progress_cmd(ctx.tools["ffmpeg"]) + inputs
    amap = []
    if m.get("audio"):
        ai = sum(1 for x in inputs if x == "-i")
        cmd += ["-i", ctx.path(m["audio"])]
        graph += ";[%d:a]afade=t=in:d=0.5,afade=t=out:st=%.3f:d=1.5[aout]" % (ai, max(0, total - 1.5))
        amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-filter_complex", graph, "-map", vlabel] + amap
    cmd += C.encoder_args(ctx.encoder, m["resolution"]["width"], m["resolution"]["height"], m["fps"])
    cmd += ["-t", "%.3f" % total, ctx.out_path]
    C.log("building video with ffmpeg (%s)" % ctx.encoder)
    C.run_ffmpeg(cmd, int(round(total * m["fps"])))


def preview(ctx, t, out_png, scale):
    spec = load_spec(ctx)
    inputs, graph, vlabel, _ = build(ctx, spec, scale)
    cmd = [ctx.tools["ffmpeg"], "-y", "-hide_banner", "-loglevel", "error"] + inputs
    cmd += ["-filter_complex", graph, "-map", vlabel, "-ss", "%.3f" % t, "-frames:v", "1", "-update", "1", out_png]
    C.stream(cmd)
