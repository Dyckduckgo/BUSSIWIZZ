#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"

PY=""
if [ -x ".venv/bin/python" ] && .venv/bin/python -c "import sys" >/dev/null 2>&1; then
    PY=".venv/bin/python"
elif [ -x "venv/bin/python" ] && venv/bin/python -c "import sys" >/dev/null 2>&1; then
    PY="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
fi

if [ -z "$PY" ]; then
    echo "[ERROR] Python 3 was not found on PATH."
    exit 1
fi

PORT_ARG=""
if [ -n "${1:-}" ]; then
    PORT_ARG="--port $1"
fi

exec "$PY" run.py --web $PORT_ARG "$@"
