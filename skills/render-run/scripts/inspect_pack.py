#!/usr/bin/env python3
"""Inspect a render pack BEFORE running anything from it.

    python3 -I inspect_pack.py PACK_DIR [--json]

Runs only trusted code (this skill's copy of local-render) and reads the pack as data:
  1. validates render.json against the schema
  2. detects the machine: OS, CPU, cores, RAM, Apple Silicon, NVIDIA GPU
  3. checks required tools and minimum versions, with install commands
  4. picks the encoder ffmpeg would use (VideoToolbox > NVENC > libx264)
  5. compares the pack's runtime/, run.sh and run.ps1 with trusted copies
  6. lists the code that will execute and flags patterns worth a look
  7. prints run.sh and the exact render command
Exit codes: 0 ready, 1 invalid pack, 3 missing tools.
"""
import hashlib
import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lr_paths as P  # noqa: E402
import lr_common as C  # noqa: E402
import lr_validate as V  # noqa: E402

KNOWN_NPM = re.compile(r"^(remotion|@remotion/[a-z0-9-]+|react|react-dom|playwright-core|zod|@types/[a-z0-9-]+|typescript)$")
RISK = {
    "ffmpeg": ("low", "data only: ffmpeg reads JSON and images; no pack code runs"),
    "html-canvas": ("medium", "pack JavaScript runs inside headless Chrome's sandbox; "
                              "local-render's own Node capture script runs outside it"),
    "remotion": ("high", "npm install runs package install scripts, and Remotion bundles and "
                         "runs the pack's TypeScript/React with Node with your user's permissions"),
    "blender": ("high", "the pack's Python script runs inside Blender with your user's permissions"),
    "manim": ("high", "the pack's Python script runs with your user's permissions"),
}
PATTERNS = {
    ".py": [r"\bsubprocess\b", r"\bos\.system\b", r"\bos\.popen\b", r"\bsocket\b", r"\burllib\b",
            r"\brequests\b", r"\bhttp\.client\b", r"\bshutil\.rmtree\b", r"\bos\.remove\b", r"\bos\.unlink\b",
            r"\beval\(", r"\bexec\(", r"\b__import__\(", r"\bctypes\b", r"\bpickle\b", r"base64",
            r"os\.environ", r"expanduser", r"open\([^)]*['\"][wa]"],
    ".js": [r"child_process", r"require\(['\"](fs|net|http|https|os)['\"]\)", r"from ['\"](node:)?(fs|net|http|https|os|child_process)['\"]",
            r"\beval\(", r"new Function\(", r"process\.env", r"https?://(?!127\.0\.0\.1|localhost)[^\s'\"]+", r"WebSocket"],
}
PATTERNS[".mjs"] = PATTERNS[".ts"] = PATTERNS[".tsx"] = PATTERNS[".jsx"] = PATTERNS[".cjs"] = PATTERNS[".js"]
PATTERNS[".html"] = [r"https?://(?!127\.0\.0\.1|localhost)[^\s'\"]+", r"<iframe", r"WebSocket"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_trusted_adapter(engine):
    path = os.path.join(P.ENGINES, engine, "adapter.py")
    spec = importlib.util.spec_from_file_location("trusted_" + engine.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path


def runtime_integrity(pack, engine):
    """Compare runtime/ and the run scripts with what local-render would generate."""
    out = {"matches": [], "differs": [], "missing": [], "extra": []}
    adapter, adapter_path = load_trusted_adapter(engine)
    expected = {name: os.path.join(P.RUNTIME, name) for name in ("lr_render.py", "lr_common.py", "lr_validate.py")}
    expected["render.schema.json"] = P.SCHEMA
    expected["adapter.py"] = adapter_path
    for name in getattr(adapter, "RUNTIME_FILES", []):
        expected[name] = os.path.join(P.ENGINES, engine, name)
    rt = os.path.join(pack, "runtime")
    for name, trusted in sorted(expected.items()):
        mine = os.path.join(rt, name)
        rel = "runtime/" + name
        if not os.path.isfile(mine):
            out["missing"].append(rel)
        elif sha(mine) == sha(trusted):
            out["matches"].append(rel)
        else:
            out["differs"].append(rel)
    if os.path.isdir(rt):
        for name in sorted(os.listdir(rt)):
            if name not in expected and name not in ("node_modules", "__pycache__", "package-lock.json"):
                out["extra"].append("runtime/" + name)
    lr_pack = _lr_pack()
    with open(os.path.join(pack, "render.json"), encoding="utf-8") as f:
        title = lr_pack.safe_comment(json.load(f).get("title", "video"))
    for name, tpl in (("run.sh", lr_pack.RUN_SH), ("run.ps1", lr_pack.RUN_PS1)):
        p = os.path.join(pack, name)
        if not os.path.isfile(p):
            out["missing"].append(name)
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            body = f.read().replace("\r\n", "\n")
        (out["matches"] if body == tpl.format(title=title) else out["differs"]).append(name)
    return out


def _lr_pack():
    spec = importlib.util.spec_from_file_location("lr_pack", os.path.join(P.ENGINES, "_build", "lr_pack.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def code_review(pack, engine):
    """List files that will execute and any lines matching risky patterns."""
    files, flags = [], []
    roots = ["src"] + (["runtime"] if engine == "html-canvas" else [])
    for root in roots:
        base = os.path.join(pack, root)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ("node_modules", "__pycache__")]
            for fn in sorted(filenames):
                ext = os.path.splitext(fn)[1].lower()
                if ext not in PATTERNS:
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, pack).replace(os.sep, "/")
                if root == "runtime":
                    continue  # covered by the integrity check
                files.append(rel)
                with open(full, encoding="utf-8", errors="replace") as f:
                    for n, line in enumerate(f, 1):
                        for pat in PATTERNS[ext]:
                            if re.search(pat, line):
                                flags.append({"file": rel, "line": n, "match": pat, "text": line.strip()[:160]})
                                break
    return files, flags


def inspect(pack):
    pack = os.path.abspath(pack)
    report = {"pack_dir": pack}
    manifest, errs = V.validate_pack(pack)
    report["valid"] = not errs
    report["errors"] = errs
    if manifest is None:
        return report
    report["manifest"] = {k: manifest.get(k) for k in ("title", "engine", "entry", "output", "resolution", "fps",
                                                         "duration", "codec", "audio", "dependencies", "engine_options")}
    report["render_command"] = manifest.get("render", {}).get("command")
    report["windows_command"] = manifest.get("render", {}).get("windows_command")
    report["engine_command"] = manifest.get("render", {}).get("engine_command")
    hw = C.detect_hardware()
    report["machine"] = hw
    engine = manifest.get("engine")
    if engine not in RISK:
        return report
    adapter, _ = load_trusted_adapter(engine)
    reqs = list(manifest.get("requires") or [])
    listed = {r.get("tool") for r in reqs if isinstance(r, dict)}
    reqs += [r for r in adapter.REQUIRES if r["tool"] not in listed]
    try:
        report["tools"] = C.check_requirements([r for r in reqs if r.get("tool") in C.TOOLS])
    except Exception as e:  # never let a weird manifest crash the inspection
        report["tools"] = []
        report["errors"].append("tool check failed: %s" % e)
    ff = C.find_tool("ffmpeg")
    if ff and getattr(adapter, "USES_FFMPEG_ENCODER", True):
        report["encoder"] = C.pick_encoder(ff, manifest.get("codec", "h264"), hw)
    elif engine == "remotion":
        report["encoder"] = "Remotion built-in" + (" + VideoToolbox" if hw["apple_silicon"] else " (x264)")
    report["risk"], report["risk_note"] = RISK[engine]
    report["runtime"] = runtime_integrity(pack, engine)
    report["code_files"], report["flags"] = code_review(pack, engine)
    npm = (manifest.get("dependencies") or {}).get("npm") or {}
    report["npm_packages"] = sorted(npm)
    report["unusual_npm_packages"] = sorted(p for p in npm if not KNOWN_NPM.match(p))
    p = os.path.join(pack, "run.sh")
    report["run.sh"] = None
    if os.path.isfile(p):
        with open(p, encoding="utf-8", errors="replace") as f:
            report["run.sh"] = f.read()
    return report


def show(r):
    line = "-" * 72
    print(line)
    if "manifest" not in r:
        print("NOT A VALID PACK: " + "; ".join(r["errors"]))
        return
    m = r["manifest"]
    print("PACK     %s" % m["title"])
    res = m.get("resolution") or {}
    print("         engine %s · %sx%s @ %s fps · %ss · output %s"
          % (m["engine"], res.get("width"), res.get("height"), m["fps"], m["duration"], m["output"]))
    print("VALID    " + ("yes" if r["valid"] else "NO"))
    for e in r["errors"]:
        print("         - " + e)
    hw = r["machine"]
    gpu = "Apple Silicon (VideoToolbox, Metal)" if hw["apple_silicon"] else (hw["nvidia_gpu"] or "none detected")
    print("MACHINE  %s · %d cores · %s GB RAM · GPU: %s · %s"
          % (hw["cpu"], hw["cpu_count"], hw["ram_gb"] or "?", gpu, hw["os"]))
    if "tools" in r:
        print("TOOLS")
        for t in r["tools"]:
            need = (" (needs >= %s)" % t["min_version"]) if t.get("min_version") else ""
            print("         %-8s %-8s %-10s%s" % (t["tool"], t["status"].upper(), t["version"] or "", need))
            if t["status"] != "ok":
                print("                  install: %s" % t["install"])
    if r.get("encoder"):
        print("ENCODER  %s" % r["encoder"])
    if "risk" in r:
        print("RISK     %s: %s" % (r["risk"].upper(), r["risk_note"]))
        rt = r["runtime"]
        if rt["differs"] or rt["missing"] or rt["extra"]:
            print("RUNTIME  DOES NOT MATCH the trusted local-render copy:")
            for k in ("differs", "missing", "extra"):
                for f in rt[k]:
                    print("         %-8s %s" % (k, f))
            print("         Fix: python3 scripts/build_pack.py finalize <pack>  (replaces them with trusted copies)")
        else:
            print("RUNTIME  matches trusted local-render %s (%d files)" % (C.VERSION, len(rt["matches"])))
        print("CODE     files that will run: %s" % (", ".join(r["code_files"]) or "none"))
        if r["npm_packages"]:
            print("NPM      %s" % ", ".join(r["npm_packages"]))
        if r["unusual_npm_packages"]:
            print("         unusual packages (review before installing): %s" % ", ".join(r["unusual_npm_packages"]))
        if r["flags"]:
            print("REVIEW   lines worth a look before approving:")
            for f in r["flags"][:40]:
                print("         %s:%d  %s" % (f["file"], f["line"], f["text"]))
            if len(r["flags"]) > 40:
                print("         ... %d more" % (len(r["flags"]) - 40))
        else:
            print("REVIEW   no risky patterns found in pack code")
    print("COMMAND  %s      (Windows: %s)" % (r["render_command"], r["windows_command"]))
    print("ENGINE   %s" % r["engine_command"])
    if r.get("run.sh"):
        print("RUN.SH")
        for ln in r["run.sh"].splitlines():
            print("         | " + ln)
    print(line)


def main(argv):
    args = [a for a in argv[1:] if a != "--json"]
    if len(args) != 1:
        print(__doc__.strip())
        return 2
    r = inspect(args[0])
    if "--json" in argv:
        print(json.dumps(r, indent=2, default=str))
    else:
        show(r)
    if not r["valid"]:
        return 1
    if any(t["status"] != "ok" for t in r.get("tools", [])):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
