#!/usr/bin/env python3
"""Render every example pack on this machine and print a timing table.

    python3 scripts/render_examples.py [engine ...]

Each example renders with its own run.sh, exactly as a user would run it.
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    only = set(sys.argv[1:])
    base = os.path.join(ROOT, "examples")
    rows, failed = [], []
    for name in sorted(os.listdir(base)):
        ex = os.path.join(base, name)
        if not os.path.isfile(os.path.join(ex, "render.json")) or (only and name not in only):
            continue
        print("\n=== %s ===" % name, flush=True)
        t0 = time.time()
        code = subprocess.call(["sh", "run.sh"], cwd=ex)
        wall = time.time() - t0
        rep = os.path.join(ex, "render-report.json")
        if code != 0 or not os.path.isfile(rep):
            failed.append(name)
            rows.append((name, "FAILED", "", "", "", "%.1fs" % wall))
            continue
        with open(rep) as f:
            r = json.load(f)
        rows.append((name, "%sx%s" % (r["width"], r["height"]), "%.2fs" % r["duration_s"], r["size"],
                     r["encoder"] or "-", "%.1fs" % r["render_seconds"]))
    print("\n| example | resolution | video length | size | encoder | render time |")
    print("|---|---|---|---|---|---|")
    for row in rows:
        print("| %s |" % " | ".join(row))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
