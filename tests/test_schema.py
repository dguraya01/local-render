"""Every example pack validates against schema/render.schema.json, and bad manifests don't.

Runs with the built-in validator always, and with `jsonschema` too when it is installed.
"""
import copy
import json
import os
import unittest
from unittest import mock

import _paths  # noqa: F401
import lr_validate as V

try:
    import jsonschema  # noqa: F401
    HAVE_JSONSCHEMA = True
except ImportError:
    HAVE_JSONSCHEMA = False


def builtin_errors(manifest):
    errors = []
    schema = V.load_schema()
    V._mini(manifest, schema, schema, "", errors)
    return errors


def full_errors(manifest):
    import jsonschema
    return [e.message for e in jsonschema.Draft202012Validator(V.load_schema()).iter_errors(manifest)]


VALIDATORS = [("builtin", builtin_errors)] + ([("jsonschema", full_errors)] if HAVE_JSONSCHEMA else [])


class SchemaFile(unittest.TestCase):
    def test_schema_is_valid_json_schema(self):
        if not HAVE_JSONSCHEMA:
            self.skipTest("jsonschema not installed")
        import jsonschema
        jsonschema.Draft202012Validator.check_schema(V.load_schema())

    def test_runtime_copy_of_schema_matches(self):
        for ex in _paths.example_dirs():
            with open(os.path.join(ex, "runtime", "render.schema.json")) as a, open(_paths.SCHEMA) as b:
                self.assertEqual(json.load(a), json.load(b), ex)


class ExamplePacks(unittest.TestCase):
    def test_there_is_one_example_per_engine(self):
        engines = {_paths.load_json(os.path.join(e, "render.json"))["engine"] for e in _paths.example_dirs()}
        self.assertEqual(engines, {"html-canvas", "remotion", "blender", "manim", "ffmpeg"})

    def test_examples_validate(self):
        for ex in _paths.example_dirs():
            manifest, errs = V.validate_pack(ex)
            self.assertEqual(errs, [], "%s: %s" % (ex, errs))
            for name, fn in VALIDATORS:
                self.assertEqual(fn(manifest), [], "%s with %s" % (ex, name))

    def test_examples_validate_without_jsonschema(self):
        with mock.patch.dict("sys.modules", {"jsonschema": None}):
            for ex in _paths.example_dirs():
                self.assertEqual(V.validate_pack(ex)[1], [], ex)

    def test_example_files_exist(self):
        for ex in _paths.example_dirs():
            for f in ("render.json", "run.sh", "run.ps1", "README.md", "runtime/lr_render.py", "runtime/adapter.py"):
                self.assertTrue(os.path.isfile(os.path.join(ex, f)), "%s missing %s" % (ex, f))


class BadManifests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_paths.EXAMPLES, "ffmpeg", "render.json")) as f:
            self.good = json.load(f)

    def assertRejected(self, change, why):
        m = copy.deepcopy(self.good)
        change(m)
        for name, fn in VALIDATORS:
            self.assertTrue(fn(m), "%s should reject: %s" % (name, why))

    def test_rejections(self):
        cases = [
            (lambda m: m.pop("engine"), "missing engine"),
            (lambda m: m.update(engine="after-effects"), "unknown engine"),
            (lambda m: m.update(entry="/etc/passwd"), "absolute entry"),
            (lambda m: m.update(entry="../../outside.py"), "parent traversal"),
            (lambda m: m.update(entry="src/../../x.py"), "nested traversal"),
            (lambda m: m.update(entry="C:/Windows/x.py"), "drive letter"),
            (lambda m: m.update(entry="src\\scene.py"), "backslash"),
            (lambda m: m.update(audio="../music.mp3"), "audio traversal"),
            (lambda m: m.update(output="../video.mp4"), "output with folder"),
            (lambda m: m.update(output="video.exe"), "output extension"),
            (lambda m: m.update(fps=0), "fps zero"),
            (lambda m: m.update(duration=-1), "negative duration"),
            (lambda m: m["resolution"].update(width=1.5), "non-integer width"),
            (lambda m: m.update(requires=[]), "empty requires"),
            (lambda m: m.update(requires=[{"tool": "curl"}]), "unknown tool"),
            (lambda m: m["render"].update(command="rm -rf ~"), "render command must be sh run.sh"),
            (lambda m: m.update(surprise=True), "unknown top-level field"),
            (lambda m: m.update(schema_version="9.9"), "unknown schema version"),
        ]
        for change, why in cases:
            with self.subTest(why=why):
                self.assertRejected(change, why)

    def test_semantic_missing_entry_file(self):
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as d:
            pack = os.path.join(d, "p")
            shutil.copytree(os.path.join(_paths.EXAMPLES, "ffmpeg"), pack)
            os.remove(os.path.join(pack, "src", "slideshow.json"))
            errs = V.validate_pack(pack)[1]
            self.assertTrue(any("does not exist" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
