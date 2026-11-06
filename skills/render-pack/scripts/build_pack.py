#!/usr/bin/env python3
"""Build, validate and zip local-render packs. Run with -h for commands.

Thin launcher: finds local-render's shared files (see lr_paths.py) and runs
engines/_build/lr_pack.py from there.
"""
import os
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lr_paths  # noqa: E402

runpy.run_path(os.path.join(lr_paths.ENGINES, "_build", "lr_pack.py"), run_name="__main__")
