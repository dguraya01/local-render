#!/usr/bin/env python3
"""Re-finalize every example pack from the current engines/ (runtime, run scripts, README).

    python3 scripts/build_examples.py           # rewrite examples/*/runtime etc.
    python3 scripts/build_examples.py --check   # fail if any example has drifted (used by tests/CI)
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "render-run", "scripts"))
import inspect_pack  # noqa: E402


def examples():
    base = os.path.join(ROOT, "examples")
    return sorted(os.path.join(base, d) for d in os.listdir(base)
                  if os.path.isfile(os.path.join(base, d, "render.json")))


def main():
    check = "--check" in sys.argv
    bad = 0
    for ex in examples():
        name = os.path.basename(ex)
        if check:
            with open(os.path.join(ex, "render.json"), encoding="utf-8") as f:
                engine = json.load(f)["engine"]
            r = inspect_pack.runtime_integrity(ex, engine)
            drift = r["differs"] + r["missing"] + r["extra"]
            print("%-12s %s" % (name, "ok" if not drift else "DRIFT: " + ", ".join(drift)))
            bad += bool(drift)
        else:
            subprocess.check_call([sys.executable, os.path.join(ROOT, "skills", "render-pack", "scripts", "build_pack.py"),
                                   "finalize", ex])
    if bad:
        print("run: python3 scripts/build_examples.py")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
