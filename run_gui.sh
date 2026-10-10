#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"

# 1. Look for working python interpreter
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
    echo "Please install Python 3.10 or newer."
    exit 1
fi

# 2. Check for Tkinter
if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
    echo "======================================================================"
    echo " [Bussiwzz] Tkinter is missing from your Python installation."
    echo "======================================================================"
    OS="$(uname -s)"
    if [ "$OS" = "Darwin" ]; then
        echo " On macOS: run 'brew install python-tk' or download Python from python.org"
    else
        echo " On Debian / Ubuntu : sudo apt update && sudo apt install -y python3-tk"
        echo " On Fedora / RHEL   : sudo dnf install -y python3-tkinter"
        echo " On Arch Linux      : sudo pacman -S tk"
    fi
    echo ""
    echo " Alternatively, start the Web Dashboard or CLI without Tkinter:"
    echo "     $PY run.py --web"
    echo "     $PY run.py --cli NVDA"
    echo "======================================================================"
    exit 1
fi

exec "$PY" run.py --gui "$@"
