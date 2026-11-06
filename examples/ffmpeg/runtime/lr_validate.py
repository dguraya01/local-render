"""Validate a render pack's render.json.

Uses the `jsonschema` package when it is installed, otherwise a small built-in
validator that covers every keyword render.schema.json uses. Standard library
only, Python 3.8+.

    python3 lr_validate.py path/to/pack-or-render.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_FRAMES = 500_000


def find_schema():
    for cand in (
        os.path.join(HERE, "render.schema.json"),
        os.path.join(HERE, "..", "..", "schema", "render.schema.json"),
        os.path.join(HERE, "..", "schema", "render.schema.json"),
    ):
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    raise FileNotFoundError("render.schema.json not found next to lr_validate.py")


def load_schema():
    with open(find_schema(), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- mini validator
_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
}


def _type_ok(value, t):
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "null":
        return value is None
    return isinstance(value, _TYPES[t])


def _resolve(root, ref):
    if not ref.startswith("#/"):
        raise ValueError("only local $ref supported: " + ref)
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _mini(value, schema, root, path, errors):
    if "$ref" in schema:
        _mini(value, _resolve(root, schema["$ref"]), root, path, errors)
    where = path or "(root)"
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, x) for x in types):
            errors.append("%s: expected %s, got %s" % (where, "/".join(types), type(value).__name__))
            return
    if "const" in schema and value != schema["const"]:
        errors.append("%s: must be %r" % (where, schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: %r is not one of %s" % (where, value, schema["enum"]))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append("%s: too short" % where)
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append("%s: too long" % where)
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append("%s: %r does not match the required pattern" % (where, value))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append("%s: must be >= %s" % (where, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            errors.append("%s: must be <= %s" % (where, schema["maximum"]))
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append("%s: must be > %s" % (where, schema["exclusiveMinimum"]))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append("%s: needs at least %d item(s)" % (where, schema["minItems"]))
        if "items" in schema:
            for i, item in enumerate(value):
                _mini(item, schema["items"], root, "%s[%d]" % (path, i), errors)
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append("%s: missing required field %r" % (where, req))
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in value.items():
            sub = (path + "." + k) if path else k
            if k in props:
                _mini(v, props[k], root, sub, errors)
            elif addl is False:
                errors.append("%s: unknown field %r" % (where, k))
            elif isinstance(addl, dict):
                _mini(v, addl, root, sub, errors)


def schema_errors(manifest, schema=None):
    schema = schema or load_schema()
    try:
        import jsonschema  # type: ignore

        v = jsonschema.Draft202012Validator(schema)
        out = []
        for e in sorted(v.iter_errors(manifest), key=lambda e: list(e.path)):
            loc = ".".join(str(p) for p in e.path) or "(root)"
            out.append("%s: %s" % (loc, e.message))
        return out
    except ImportError:
        errors = []
        _mini(manifest, schema, schema, "", errors)
        return errors


# ---------------------------------------------------------------- semantic checks
ENGINE_TOOLS = {
    "html-canvas": ["ffmpeg", "node"],
    "remotion": ["node"],
    "blender": ["blender", "ffmpeg"],
    "manim": ["manim"],
    "ffmpeg": ["ffmpeg"],
}


def _inside(pack_dir, rel):
    full = os.path.realpath(os.path.join(pack_dir, rel))
    root = os.path.realpath(pack_dir)
    return full == root or full.startswith(root + os.sep)


def semantic_errors(manifest, pack_dir):
    errs = []
    if not isinstance(manifest, dict):
        return errs
    for key in ("entry", "audio"):
        rel = manifest.get(key)
        if isinstance(rel, str):
            if not _inside(pack_dir, rel):
                errs.append("%s: %r points outside the pack" % (key, rel))
            elif not os.path.isfile(os.path.join(pack_dir, rel)):
                errs.append("%s: file %r does not exist in the pack" % (key, rel))
    npm_dir = (manifest.get("dependencies") or {}).get("npm_dir")
    if isinstance(npm_dir, str) and not os.path.isfile(os.path.join(pack_dir, npm_dir, "package.json")):
        errs.append("dependencies.npm_dir: no package.json in %r" % npm_dir)
    try:
        frames = float(manifest["fps"]) * float(manifest["duration"])
        if frames > MAX_FRAMES:
            errs.append("fps x duration = %d frames, over the %d frame limit" % (frames, MAX_FRAMES))
    except (KeyError, TypeError, ValueError):
        pass
    listed = {r.get("tool") for r in manifest.get("requires", []) if isinstance(r, dict)}
    for tool in ENGINE_TOOLS.get(manifest.get("engine"), []):
        if tool not in listed:
            errs.append("requires: engine %r needs %r listed" % (manifest.get("engine"), tool))
    for dirpath, dirnames, filenames in os.walk(pack_dir):
        dirnames[:] = [d for d in dirnames if d != "node_modules"]
        for name in dirnames + filenames:
            p = os.path.join(dirpath, name)
            if os.path.islink(p):
                errs.append("symlink not allowed in a pack: %s" % os.path.relpath(p, pack_dir))
    return errs


def load_manifest(path):
    if os.path.isdir(path):
        path = os.path.join(path, "render.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f), os.path.dirname(os.path.abspath(path))


def validate_pack(path):
    """Return (manifest, errors). errors is empty when the pack is valid."""
    try:
        manifest, pack_dir = load_manifest(path)
    except FileNotFoundError:
        return None, ["render.json not found"]
    except json.JSONDecodeError as e:
        return None, ["render.json is not valid JSON: %s" % e]
    errs = schema_errors(manifest)
    errs += semantic_errors(manifest, pack_dir)
    return manifest, errs


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    manifest, errs = validate_pack(argv[1])
    if errs:
        print("INVALID render pack:")
        for e in errs:
            print("  - " + e)
        return 1
    print("OK: %s (%s, %dx%d @ %sfps, %ss)" % (
        manifest["title"], manifest["engine"], manifest["resolution"]["width"],
        manifest["resolution"]["height"], manifest["fps"], manifest["duration"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
