"""Locate local-render's shared files (engines/ and schema/).

Search order:
  1. $LOCAL_RENDER_HOME
  2. <skill>/shared/          (packaged skill zips and ~/.claude/skills installs)
  3. <skill>/../../           (running from a repo checkout or the Claude Code plugin)
"""
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ok(root):
    return (os.path.isfile(os.path.join(root, "engines", "_runtime", "lr_render.py"))
            and os.path.isfile(os.path.join(root, "schema", "render.schema.json")))


def shared_root():
    cands = [os.environ.get("LOCAL_RENDER_HOME"), os.path.join(SKILL_DIR, "shared"),
             os.path.join(SKILL_DIR, "..", "..")]
    for c in cands:
        if c and _ok(c):
            return os.path.abspath(c)
    sys.exit("local-render: cannot find engines/ and schema/. Set LOCAL_RENDER_HOME to the repo folder.")


ROOT = shared_root()
ENGINES = os.path.join(ROOT, "engines")
RUNTIME = os.path.join(ENGINES, "_runtime")
SCHEMA = os.path.join(ROOT, "schema", "render.schema.json")
if RUNTIME not in sys.path:
    sys.path.insert(0, RUNTIME)
