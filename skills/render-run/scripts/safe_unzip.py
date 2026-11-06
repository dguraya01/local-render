#!/usr/bin/env python3
"""Safely extract a render pack zip into a NEW folder.

    python3 -I safe_unzip.py PACK.zip [DEST]

DEST defaults to a new folder next to the zip, named after it. Nothing is written unless
every entry passes the checks (all-or-nothing):
  - no absolute paths, drive letters, UNC paths, backslashes or NUL bytes
  - no '..' path segments (zip-slip) and every resolved path stays inside DEST
  - no symlinks, devices or other special files; no duplicate names
  - zip-bomb limits: entry count, total size, per-entry size and compression ratio
Executable bits are dropped; files are written 0644, folders 0755.
Prints the pack folder (the one holding render.json) as the last line: PACK_DIR=<path>
Exit codes: 0 ok, 1 rejected, 2 usage.
"""
import os
import re
import shutil
import stat
import sys
import zipfile

MAX_ENTRIES = 20_000
MAX_TOTAL = 4 * 2 ** 30         # 4 GB uncompressed
MAX_ENTRY = 2 * 2 ** 30         # 2 GB per file
MAX_RATIO = 250                 # compression ratio considered a bomb (for entries > 1 MB)
IGNORED = re.compile(r"(^|/)(__MACOSX/|\.DS_Store$|Thumbs\.db$)")


class Rejected(Exception):
    pass


def check_name(name):
    if not name or "\x00" in name:
        raise Rejected("empty name or NUL byte in entry name")
    if "\\" in name:
        raise Rejected("backslash in entry name: %r" % name)
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name) or name.startswith("//"):
        raise Rejected("absolute path: %r" % name)
    parts = name.rstrip("/").split("/")
    if any(p == ".." for p in parts):
        raise Rejected("'..' path segment (zip-slip): %r" % name)
    if any(p == "" for p in parts):
        raise Rejected("empty path segment: %r" % name)


def entry_kind(info):
    mode = (info.external_attr >> 16) & 0xFFFF
    if info.is_dir():
        return "dir"
    if mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG):
        return "special"  # symlink (S_IFLNK), device, fifo, socket
    return "file"


def plan(zf, dest):
    root = os.path.realpath(dest)
    seen, total, items = set(), 0, []
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise Rejected("too many entries (%d > %d)" % (len(infos), MAX_ENTRIES))
    for info in infos:
        name = info.filename
        if IGNORED.search(name):
            continue
        check_name(name)
        kind = entry_kind(info)
        if kind == "special":
            raise Rejected("symlink or special file not allowed: %r" % name)
        key = name.rstrip("/").lower()
        if key in seen:
            raise Rejected("duplicate entry (case-insensitive): %r" % name)
        seen.add(key)
        target = os.path.realpath(os.path.join(root, *name.rstrip("/").split("/")))
        if not (target == root or target.startswith(root + os.sep)):
            raise Rejected("entry escapes the destination: %r" % name)
        if kind == "file":
            if info.file_size > MAX_ENTRY:
                raise Rejected("entry too large: %r" % name)
            if info.file_size > 2 ** 20 and info.compress_size and info.file_size / info.compress_size > MAX_RATIO:
                raise Rejected("suspicious compression ratio (zip bomb?): %r" % name)
            total += info.file_size
            if total > MAX_TOTAL:
                raise Rejected("pack is larger than %d GB uncompressed" % (MAX_TOTAL // 2 ** 30))
        items.append((info, kind, target))
    if not items:
        raise Rejected("zip is empty")
    return items


def extract(zip_path, dest):
    if os.path.exists(dest):
        raise Rejected("destination already exists: %s (choose a new folder)" % dest)
    with zipfile.ZipFile(zip_path) as zf:
        items = plan(zf, dest)  # validates everything before writing anything
        os.makedirs(dest, mode=0o755)
        try:
            _write(zf, items)
        except BaseException:
            shutil.rmtree(dest, ignore_errors=True)  # dest is new (checked above), so removing it is safe
            raise
    return find_pack_root(dest)


def _write(zf, items):
    written = 0
    for info, kind, target in items:
        if kind == "dir":
            os.makedirs(target, mode=0o755, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(target), mode=0o755, exist_ok=True)
        remaining = info.file_size
        with zf.open(info) as src, open(target, "xb") as out:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                remaining -= len(chunk)
                written += len(chunk)
                if remaining < 0 or written > MAX_TOTAL:  # header lied about the size
                    raise Rejected("entry is larger than its header says: %r" % info.filename)
                out.write(chunk)
        os.chmod(target, 0o644)


def find_pack_root(dest):
    if os.path.isfile(os.path.join(dest, "render.json")):
        return dest
    subs = [d for d in os.listdir(dest) if os.path.isdir(os.path.join(dest, d))]
    if len(subs) == 1 and os.path.isfile(os.path.join(dest, subs[0], "render.json")):
        return os.path.join(dest, subs[0])
    raise Rejected("no render.json at the top of the zip; this is not a render pack")


def default_dest(zip_path):
    base = os.path.splitext(os.path.abspath(zip_path))[0]
    dest, n = base, 2
    while os.path.exists(dest):
        dest, n = "%s-%d" % (base, n), n + 1
    return dest


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__.strip())
        return 2
    zip_path = argv[1]
    dest = os.path.abspath(argv[2]) if len(argv) == 3 else default_dest(zip_path)
    try:
        if not zipfile.is_zipfile(zip_path):
            raise Rejected("not a zip file: %s" % zip_path)
        pack = extract(zip_path, dest)
    except Rejected as e:
        print("REJECTED: %s" % e)
        if os.path.isdir(dest) and not os.listdir(dest):
            os.rmdir(dest)
        return 1
    print("extracted safely to %s" % dest)
    print("PACK_DIR=%s" % pack)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
