#!/bin/sh
set -eu

cd -- "$(dirname -- "$0")/.."
PYTHON=${PYTHON:-.venv/bin/python}

if [ ! -x "$PYTHON" ]; then
    echo "Chưa có môi trường build. Cài bằng: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-build.txt" >&2
    exit 1
fi

"$PYTHON" -m compileall -q mailnotes packaging
"$PYTHON" -m unittest discover -s tests -v
node --check chrome-extension/content.js
node --check chrome-extension/worker.js
node --check chrome-extension/popup.js
node tests/extension_download.cjs
"$PYTHON" packaging/smoke_extension_ui.py
"$PYTHON" packaging/smoke_extension_download.py

echo "Go-live checks passed. Gmail thật, GreenNode thật và máy Mac khách vẫn cần nghiệm thu theo deploy/GO-LIVE.md."
