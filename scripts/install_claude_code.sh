#!/bin/sh
# Install the skills into ~/.claude/skills (personal skills for Claude Code), without the plugin.
#   sh scripts/install_claude_code.sh           # refuses to overwrite existing copies
#   sh scripts/install_claude_code.sh --force   # replace existing copies
set -e
cd "$(dirname "$0")/.."
sh scripts/package_skills.sh >/dev/null
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"
for skill in render-pack render-run; do
  if [ -e "$DEST/$skill" ]; then
    if [ "$1" = "--force" ]; then
      rm -rf "$DEST/$skill"
    else
      echo "$DEST/$skill already exists. Re-run with --force to replace it."
      exit 1
    fi
  fi
  cp -R "dist/skills/$skill" "$DEST/$skill"
  echo "installed $DEST/$skill"
done
echo "Restart Claude Code, then ask it to render a pack."
