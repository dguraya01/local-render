import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples")
SCHEMA = os.path.join(ROOT, "schema", "render.schema.json")
for p in (os.path.join(ROOT, "engines", "_runtime"), os.path.join(ROOT, "skills", "render-run", "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)


def example_dirs():
    return sorted(os.path.join(EXAMPLES, d) for d in os.listdir(EXAMPLES)
                  if os.path.isfile(os.path.join(EXAMPLES, d, "render.json")))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_json(path):
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)
