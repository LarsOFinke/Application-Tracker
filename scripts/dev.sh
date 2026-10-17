#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

supported_python() {
    "$1" -c 'import sys; sys.exit(not ((3, 11) <= sys.version_info[:2] < (3, 14)))' \
        >/dev/null 2>&1
}

if [[ -n "${DEV_PYTHON:-}" ]]; then
    dev_python="$DEV_PYTHON"
    supported_python "$dev_python" || {
        echo 'DEV_PYTHON must use Python 3.11–3.13.' >&2
        exit 1
    }
else
    dev_python="$PWD/.venv/bin/python"
    if [[ ! -x "$dev_python" ]] || ! supported_python "$dev_python"; then
        python_bin="${PYTHON_BIN:-}"
        if [[ -z "$python_bin" ]]; then
            for candidate in python3.13 python3.12 python3.11 \
                "$HOME"/Projekte/*/.tools/python/cpython-3.13/bin/python3.13; do
                if command -v "$candidate" >/dev/null 2>&1 && supported_python "$candidate"; then
                    python_bin="$candidate"
                    break
                fi
            done
        fi
        [[ -n "$python_bin" ]] && supported_python "$python_bin" || {
            echo 'Python 3.11–3.13 is required. Set PYTHON_BIN to a compatible interpreter.' >&2
            exit 1
        }
        if [[ -e .venv ]]; then
            [[ -f .venv/pyvenv.cfg ]] || { echo '.venv exists but is not a virtual environment' >&2; exit 1; }
            rm -rf .venv
        fi
        "$python_bin" -m venv .venv
        echo "Created .venv with $($dev_python -V)"
    fi
    if ! "$dev_python" -c 'import kivy, sqlalchemy, pytest, ruff; import importlib.metadata; importlib.metadata.version("application-tracker")' >/dev/null 2>&1; then
        "$dev_python" -m pip install -e '.[dev]'
    fi
fi

"$dev_python" -c 'import kivy, sqlalchemy' >/dev/null
PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" exec "$dev_python" -m application_tracker.app
