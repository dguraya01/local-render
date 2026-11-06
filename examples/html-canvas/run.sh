#!/bin/sh
# local-render: renders "Write in the cloud. Render at home." on this computer.
# Usage:  sh run.sh            render the video
#         sh run.sh --check    only check that the needed tools are installed
#         sh run.sh --preview  render one small test frame (preview.png)
# All the work happens in runtime/lr_render.py (plain Python, standard library only).
cd "$(dirname "$0")" || exit 1
for PY in python3 python; do
  if command -v "$PY" >/dev/null 2>&1 && "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
    exec "$PY" -I runtime/lr_render.py "$@"
  fi
done
echo "Python 3.8 or newer is needed to render this video."
echo "  macOS:  brew install python   (or https://www.python.org/downloads/)"
echo "  Linux:  sudo apt install python3"
exit 1
