#!/bin/bash
cd "$(dirname "$0")" || exit 1
if [ -n "${POLYMERGE_ML_PYTHON:-}" ] && [ -x "$POLYMERGE_ML_PYTHON" ]; then
  "$POLYMERGE_ML_PYTHON" scripts/local_demo.py setup "$@"
elif [ -x ".venv-demo-ml/bin/python" ]; then
  ".venv-demo-ml/bin/python" scripts/local_demo.py setup "$@"
elif command -v python3.11 >/dev/null 2>&1; then
  python3.11 scripts/local_demo.py setup "$@"
else
  printf '%s\n' 'Python 3.11 is required. See docs/LOCAL_SETUP.md.'
  exit 1
fi
code=$?
if [ "$code" -ne 0 ]; then read -r -p 'Press Enter to close...' _; fi
exit "$code"
