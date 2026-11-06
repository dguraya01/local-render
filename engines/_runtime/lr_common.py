"""Shared helpers for local-render: tool discovery, hardware detection,
encoder selection, streaming subprocesses with progress, and ffmpeg encoding.

Standard library only, Python 3.8+. This file is copied into every render
pack (runtime/) and also used by the render-run skill's inspection scripts.
"""
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

VERSION = "1.0.0"
PREFIX = "[local-render]"

# Windows consoles often use a legacy code page; never crash on a non-ASCII character.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def log(msg=""):
    print("%s %s" % (PREFIX, msg) if msg else "", flush=True)


def os_key():
    s = platform.system()
    return {"Darwin": "mac", "Windows": "windows"}.get(s, "linux")


# ------------------------------------------------------------------ tools
def _app_paths(tool):
    home = os.path.expanduser("~")
    if tool == "blender":
        paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            os.path.join(home, "Applications/Blender.app/Contents/MacOS/Blender"),
            "/snap/bin/blender",
            "/usr/bin/blender",
            "/opt/blender/blender",
        ]
        paths += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"), reverse=True)
        paths += sorted(glob.glob("/Applications/Blender*.app/Contents/MacOS/Blender"), reverse=True)
        return paths
    if tool == "chrome":
        pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium",
            os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
        ]
    if tool == "manim":
        return [os.path.join(home, ".local/bin/manim")]
    return []


TOOLS = {
    "ffmpeg": {
        "names": ["ffmpeg"], "args": ["-version"], "re": r"ffmpeg version n?(\d+(?:\.\d+)*)",
        "install": {"mac": "brew install ffmpeg", "windows": "winget install --id Gyan.FFmpeg -e",
                    "linux": "sudo apt install ffmpeg"},
    },
    "ffprobe": {
        "names": ["ffprobe"], "args": ["-version"], "re": r"ffprobe version n?(\d+(?:\.\d+)*)",
        "install": {"mac": "brew install ffmpeg", "windows": "winget install --id Gyan.FFmpeg -e",
                    "linux": "sudo apt install ffmpeg"},
    },
    "node": {
        "names": ["node"], "args": ["--version"], "re": r"v?(\d+\.\d+\.\d+)",
        "install": {"mac": "brew install node", "windows": "winget install --id OpenJS.NodeJS.LTS -e",
                    "linux": "sudo apt install nodejs npm   (or use nvm: https://github.com/nvm-sh/nvm)"},
    },
    "npm": {
        "names": ["npm", "npm.cmd"], "args": ["--version"], "re": r"(\d+\.\d+\.\d+)",
        "install": {"mac": "brew install node", "windows": "winget install --id OpenJS.NodeJS.LTS -e",
                    "linux": "sudo apt install npm"},
    },
    "python": {
        "names": ["python3", "python"], "args": ["--version"], "re": r"Python (\d+\.\d+\.\d+)",
        "install": {"mac": "brew install python", "windows": "winget install --id Python.Python.3.12 -e",
                    "linux": "sudo apt install python3"},
    },
    "blender": {
        "names": ["blender"], "args": ["--version"], "re": r"Blender (\d+\.\d+(?:\.\d+)?)",
        "install": {"mac": "brew install --cask blender", "windows": "winget install --id BlenderFoundation.Blender -e",
                    "linux": "sudo snap install blender --classic"},
    },
    "manim": {
        "names": ["manim"], "args": ["--version"], "re": r"v?(\d+\.\d+\.\d+)",
        "install": {"mac": "brew install uv pkg-config cairo pango && uv tool install manim --python 3.12",
                    "windows": "winget install --id astral-sh.uv -e; uv tool install manim --python 3.12",
                    "linux": "sudo apt install libcairo2-dev libpango1.0-dev pkg-config && uv tool install manim --python 3.12"},
    },
    "chrome": {
        "names": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"],
        "args": None, "re": None,
        "install": {"mac": "brew install --cask google-chrome", "windows": "winget install --id Google.Chrome -e",
                    "linux": "Install Google Chrome or Chromium (or run: npx playwright install chromium)"},
    },
}

_tool_cache = {}


def find_tool(tool):
    """Return the absolute path to a tool, or None. LR_<TOOL> env vars override."""
    if tool in _tool_cache:
        return _tool_cache[tool]
    path = None
    env = os.environ.get("LR_" + tool.upper().replace("-", "_"))
    if env and os.path.isfile(env):
        path = env
    if not path and tool == "python":
        path = sys.executable
    if not path:
        for n in TOOLS[tool]["names"]:
            p = shutil.which(n)
            if p:
                path = p
                break
    if not path:
        for p in _app_paths(tool):
            if p and os.path.isfile(p):
                path = p
                break
    _tool_cache[tool] = path
    return path


def tool_version(tool, path=None):
    info = TOOLS[tool]
    path = path or find_tool(tool)
    if not path or not info["args"]:
        return None
    try:
        out = subprocess.run([path] + info["args"], capture_output=True, text=True, timeout=60,
                             errors="replace")
        m = re.search(info["re"], (out.stdout or "") + (out.stderr or ""))
        return m.group(1) if m else None
    except (OSError, subprocess.SubprocessError):
        return None


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3]) or (0,)


def check_requirements(requires):
    """Check manifest `requires` entries. Returns list of dicts with status."""
    results = []
    for req in requires:
        tool = req["tool"]
        path = find_tool(tool)
        ver = tool_version(tool, path) if path else None
        need = req.get("min_version")
        if not path:
            status = "missing"
        elif need and ver and vtuple(ver) < vtuple(need):
            status = "too_old"
        else:
            status = "ok"
        results.append({
            "tool": tool, "path": path, "version": ver, "min_version": need, "status": status,
            "install": TOOLS[tool]["install"][os_key()],
        })
    return results


# ------------------------------------------------------------------ hardware
def _cmd_out(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def detect_hardware():
    system = platform.system()
    machine = platform.machine().lower()
    hw = {"os": os_key(), "os_version": platform.platform(), "arch": machine,
          "cpu_count": os.cpu_count() or 1, "cpu": platform.processor() or machine,
          "apple_silicon": False, "nvidia_gpu": None, "ram_gb": None}
    if system == "Darwin":
        hw["cpu"] = _cmd_out(["sysctl", "-n", "machdep.cpu.brand_string"]) or hw["cpu"]
        hw["apple_silicon"] = machine == "arm64" or _cmd_out(["sysctl", "-n", "hw.optional.arm64"]) == "1"
        mem = _cmd_out(["sysctl", "-n", "hw.memsize"])
        hw["ram_gb"] = round(int(mem) / 2 ** 30) if mem.isdigit() else None
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                m = re.search(r"model name\s*:\s*(.+)", f.read())
                hw["cpu"] = m.group(1).strip() if m else hw["cpu"]
            with open("/proc/meminfo") as f:
                m = re.search(r"MemTotal:\s*(\d+)", f.read())
                hw["ram_gb"] = round(int(m.group(1)) / 2 ** 20) if m else None
        except OSError:
            pass
    smi = shutil.which("nvidia-smi")
    if smi:
        name = _cmd_out([smi, "--query-gpu=name", "--format=csv,noheader"]).splitlines()
        hw["nvidia_gpu"] = name[0].strip() if name else None
    return hw


# ------------------------------------------------------------------ encoders
CANDIDATES = {
    "h264": ["h264_videotoolbox", "h264_nvenc", "libx264"],
    "hevc": ["hevc_videotoolbox", "hevc_nvenc", "libx265"],
}
_probe_cache = {}


def encoder_works(ffmpeg, name):
    """Listed encoders can still fail (e.g. NVENC without a GPU), so test-encode a few frames."""
    key = (ffmpeg, name)
    if key not in _probe_cache:
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
               "color=c=black:s=256x256:r=30:d=0.2", "-c:v", name, "-pix_fmt", "yuv420p", "-f", "null", "-"]
        try:
            _probe_cache[key] = subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0
        except (OSError, subprocess.SubprocessError):
            _probe_cache[key] = False
    return _probe_cache[key]


def pick_encoder(ffmpeg, codec="h264", hw=None, override=None):
    """Return the fastest working encoder name for the codec family."""
    override = override or os.environ.get("LR_ENCODER")
    if override:
        return override
    hw = hw or detect_hardware()
    for name in CANDIDATES[codec]:
        if "videotoolbox" in name and hw["os"] != "mac":
            continue
        if "nvenc" in name and not hw["nvidia_gpu"]:
            continue
        if encoder_works(ffmpeg, name):
            return name
    return CANDIDATES[codec][-1]


def encoder_args(name, width, height, fps):
    mbps = max(2, int(round(width * height * fps * 0.15 / 1e6)))
    if "videotoolbox" in name:
        args = ["-c:v", name, "-b:v", "%dM" % mbps, "-maxrate", "%dM" % (mbps * 2), "-bufsize", "%dM" % (mbps * 2)]
    elif "nvenc" in name:
        args = ["-c:v", name, "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "21", "-b:v", "0"]
    elif name == "libx265":
        args = ["-c:v", name, "-preset", "fast", "-crf", "22"]
    elif name == "libx264":
        args = ["-c:v", name, "-preset", "fast", "-crf", "18"]
    else:
        args = ["-c:v", name]
    if name.startswith("hevc") or name == "libx265":
        args += ["-tag:v", "hvc1"]
    return args + ["-pix_fmt", "yuv420p", "-movflags", "+faststart"]


# ------------------------------------------------------------------ processes
def stream(cmd, cwd=None, env=None, on_line=None, echo=True):
    """Run cmd, splitting output on \\n and \\r so progress bars become lines.
    on_line(line) may return False to suppress echo. Raises on non-zero exit."""
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    buf = b""
    tail = []

    def emit(raw):
        line = raw.decode("utf-8", "replace").rstrip()
        if not line:
            return
        tail.append(line)
        del tail[:-40]
        show = on_line(line) if on_line else True
        if echo and show is not False:
            print("    " + line, flush=True)

    while True:
        chunk = proc.stdout.read1(65536) if hasattr(proc.stdout, "read1") else proc.stdout.read(4096)
        if not chunk:
            break
        buf += chunk
        parts = re.split(rb"[\r\n]", buf)
        buf = parts.pop()
        for p in parts:
            emit(p)
    if buf:
        emit(buf)
    code = proc.wait()
    if code != 0:
        raise RuntimeError("command failed (exit %d): %s\n--- last output ---\n%s"
                           % (code, " ".join(str(c) for c in cmd), "\n".join(tail[-15:])))


class Progress:
    """Prints one line per 5% step, with elapsed time and ETA."""

    def __init__(self, total, label="frames", step=5):
        self.total = max(1, int(total))
        self.label = label
        self.step = step
        self.last = -1
        self.t0 = time.time()

    def update(self, done):
        pct = int(min(done, self.total) * 100 / self.total)
        bucket = pct - pct % self.step
        if bucket <= self.last:
            return
        self.last = bucket
        el = time.time() - self.t0
        eta = (el / done * (self.total - done)) if done else 0
        log("progress %3d%%  %d/%d %s  elapsed %s  eta %s"
            % (pct, min(done, self.total), self.total, self.label, fmt_secs(el), fmt_secs(eta)))


def fmt_secs(s):
    s = int(round(s))
    return "%dm%02ds" % (s // 60, s % 60) if s >= 60 else "%ds" % s


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%.1f %s" % (n, unit)) if unit != "B" else "%d B" % n
        n /= 1024.0


def probe(path):
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        return {}
    out = _cmd_out([ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    try:
        data = json.loads(out)
    except ValueError:
        return {}
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    return {
        "duration": float(data.get("format", {}).get("duration", 0) or 0),
        "width": v.get("width"), "height": v.get("height"), "codec": v.get("codec_name"),
        "frames": int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None,
        "audio": a.get("codec_name") if a else None,
    }


def ffmpeg_progress_cmd(ffmpeg):
    return [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-nostats", "-progress", "pipe:1"]


def run_ffmpeg(args, total_frames, label="frames encoded"):
    """Run an ffmpeg command built with ffmpeg_progress_cmd(), turning -progress output into lines."""
    prog = Progress(total_frames, label)

    def on_line(line):
        if line.startswith("frame="):
            try:
                prog.update(int(line.split("=", 1)[1]))
            except ValueError:
                pass
            return False
        if re.match(r"^[a-z0-9_]+=", line):
            return False  # other -progress key=value lines
        return True

    stream(args, on_line=on_line)


def encode_frames(ctx, pattern, start_number=1):
    """Encode an image sequence (printf-style pattern) to ctx.out_path with the chosen encoder."""
    fps = ctx.manifest["fps"]
    encode(ctx, ["-framerate", str(fps), "-start_number", str(start_number), "-i", pattern])


def encode_video(ctx, path):
    """Re-encode an intermediate video file to ctx.out_path with the chosen encoder."""
    encode(ctx, ["-i", path])


def encode(ctx, input_args):
    """Encode input 0 (plus render.json audio, if any) to ctx.out_path."""
    m = ctx.manifest
    w, h, fps = m["resolution"]["width"], m["resolution"]["height"], m["fps"]
    cmd = ffmpeg_progress_cmd(ctx.tools["ffmpeg"]) + list(input_args)
    audio = m.get("audio")
    if audio:
        cmd += ["-i", os.path.join(ctx.pack_dir, audio)]
    cmd += ["-map", "0:v:0"]
    if audio:
        cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k",
                "-af", "afade=t=out:st=%.3f:d=1" % max(0, m["duration"] - 1)]
    cmd += ["-vf", "scale=%d:%d:flags=lanczos,fps=%s,format=yuv420p" % (w, h, fps)]
    cmd += encoder_args(ctx.encoder, w, h, fps)
    cmd += ["-t", "%.3f" % m["duration"], ctx.out_path]
    log("encoding with %s" % ctx.encoder)
    run_ffmpeg(cmd, ctx.total_frames)
