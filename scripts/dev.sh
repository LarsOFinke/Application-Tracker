#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -n "${DEV_PYTHON:-}" ]]; then
    dev_python="$DEV_PYTHON"
else
    dev_python="$PWD/.venv/bin/python"
    if [[ ! -x "$dev_python" ]]; then
        python_bin="${PYTHON_BIN:-}"
        if [[ -z "$python_bin" ]]; then
            for candidate in python3.13 python3.12 python3.11 python3.14 python3; do
                if command -v "$candidate" >/dev/null 2>&1; then
                    python_bin="$candidate"
                    break
                fi
            done
        fi
        [[ -n "$python_bin" ]] || { echo 'Python 3.11–3.14 is required' >&2; exit 1; }
        "$python_bin" -m venv .venv
    fi
    if ! "$dev_python" -c 'import kivy, sqlalchemy' >/dev/null 2>&1; then
        "$dev_python" -m pip install -e .
    fi
fi

"$dev_python" -c 'import kivy, sqlalchemy' >/dev/null
PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" exec "$dev_python" -m application_tracker.app
