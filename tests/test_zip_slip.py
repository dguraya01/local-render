"""safe_unzip.py must refuse anything that could write outside the new folder."""
import io
import os
import stat
import tempfile
import unittest
import zipfile

import _paths  # noqa: F401
import safe_unzip as SU

MANIFEST = b'{"schema_version": "1.0"}'


def make_zip(path, entries, symlinks=()):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            z.writestr(name, data)
        for name, target in symlinks:
            zi = zipfile.ZipInfo(name)
            zi.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(zi, target)


class ZipSlip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.zip = os.path.join(self.root, "pack.zip")
        self.dest = os.path.join(self.root, "out", "pack")
        os.makedirs(os.path.dirname(self.dest))

    def tearDown(self):
        self.tmp.cleanup()

    def everything_outside_dest(self):
        found = []
        for dirpath, _, files in os.walk(self.root):
            for f in files:
                p = os.path.join(dirpath, f)
                if p != self.zip and not p.startswith(self.dest + os.sep):
                    found.append(p)
        return found

    def assertRejects(self, entries, symlinks=(), why=""):
        make_zip(self.zip, [("render.json", MANIFEST)] + entries, symlinks)
        with self.assertRaises(SU.Rejected, msg=why):
            SU.extract(self.zip, self.dest)
        self.assertFalse(os.path.exists(self.dest), "destination should not be left behind: " + why)
        self.assertEqual(self.everything_outside_dest(), [], why)

    def test_parent_traversal(self):
        self.assertRejects([("../evil.txt", b"x")], why="../")

    def test_nested_traversal(self):
        self.assertRejects([("src/../../evil.txt", b"x")], why="src/../../")

    def test_deep_traversal(self):
        self.assertRejects([("a/b/../../../../../tmp/evil.txt", b"x")], why="deep ../")

    def test_absolute_posix(self):
        self.assertRejects([("/tmp/evil.txt", b"x")], why="absolute")

    def test_windows_drive(self):
        self.assertRejects([("C:/Windows/evil.txt", b"x")], why="drive letter")

    def test_backslash_traversal(self):
        self.assertRejects([("..\\evil.txt", b"x")], why="backslash ..")

    def test_unc_path(self):
        self.assertRejects([("//server/share/evil.txt", b"x")], why="UNC")

    def test_symlink_entry(self):
        self.assertRejects([], symlinks=[("src/link", "/etc/passwd")], why="symlink")

    def test_symlink_then_write_through_it(self):
        self.assertRejects([("src/link/evil.txt", b"x")], symlinks=[("src/link", "../../..")], why="symlink dir")

    def test_duplicate_names(self):
        self.assertRejects([("src/a.txt", b"1"), ("SRC/A.txt", b"2")], why="case-insensitive duplicate")

    def test_zip_bomb_ratio(self):
        self.assertRejects([("assets/zeros.bin", b"\0" * (50 * 2 ** 20))], why="compression bomb")

    def test_destination_must_be_new(self):
        make_zip(self.zip, [("render.json", MANIFEST)])
        os.makedirs(self.dest)
        with self.assertRaises(SU.Rejected):
            SU.extract(self.zip, self.dest)

    def test_not_a_pack(self):
        make_zip(self.zip, [("hello.txt", b"hi")])
        with self.assertRaises(SU.Rejected):
            SU.extract(self.zip, self.dest)
        self.assertFalse(os.path.exists(self.dest) and os.listdir(self.dest) == [])

    def test_cli_reports_rejection(self):
        make_zip(self.zip, [("render.json", MANIFEST), ("../evil.txt", b"x")])
        buf = io.StringIO()
        from contextlib import redirect_stdout
        with redirect_stdout(buf):
            code = SU.main(["safe_unzip.py", self.zip, self.dest])
        self.assertEqual(code, 1)
        self.assertIn("REJECTED", buf.getvalue())

    def test_good_pack_extracts(self):
        make_zip(self.zip, [("render.json", MANIFEST), ("src/a.js", b"1"), ("run.sh", b"#!/bin/sh"),
                            ("__MACOSX/._run.sh", b"junk")])
        pack = SU.extract(self.zip, self.dest)
        self.assertEqual(pack, self.dest)
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "src", "a.js")))
        self.assertFalse(os.path.exists(os.path.join(self.dest, "__MACOSX")))
        mode = stat.S_IMODE(os.stat(os.path.join(self.dest, "run.sh")).st_mode)
        self.assertEqual(mode & 0o111, 0, "exec bits must be dropped")

    def test_pack_inside_single_folder(self):
        make_zip(self.zip, [("my-pack/render.json", MANIFEST), ("my-pack/src/a.js", b"1")])
        self.assertEqual(SU.extract(self.zip, self.dest), os.path.join(self.dest, "my-pack"))


if __name__ == "__main__":
    unittest.main()
