#!/bin/sh
# Build self-contained, uploadable skill zips for claude.ai:
#   dist/render-pack.zip   dist/render-run.zip
# Each zip holds one folder <skill>/ with SKILL.md, scripts/, references/ and
# shared/ (a copy of engines/ and schema/), so the skill works without this repo.
# The unzipped folders are left in dist/skills/ for ~/.claude/skills installs.
set -e
cd "$(dirname "$0")/.."
command -v zip >/dev/null 2>&1 || { echo "zip is required (brew install zip / apt install zip)"; exit 1; }

rm -rf dist/skills dist/render-pack.zip dist/render-run.zip
mkdir -p dist/skills

for skill in render-pack render-run; do
  out="dist/skills/$skill"
  mkdir -p "$out/shared"
  cp -R "skills/$skill/." "$out/"
  cp -R engines "$out/shared/engines"
  cp -R schema "$out/shared/schema"
  find "$out" \( -name __pycache__ -o -name node_modules \) -prune -exec rm -rf {} +
  find "$out" \( -name .DS_Store -o -name '*.pyc' \) -delete
  (cd dist/skills && zip -qrX "../$skill.zip" "$skill")
  echo "built dist/$skill.zip ($(du -h "dist/$skill.zip" | cut -f1 | tr -d ' '))"
done

echo
echo "claude.ai: Settings > Capabilities > Skills > Upload skill, once per zip."
