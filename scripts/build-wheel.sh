#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python_bin="${PYTHON_BIN:-.venv/bin/python}"
"$python_bin" -c 'import sys; sys.exit(not ((3, 11) <= sys.version_info[:2] < (3, 14)))' || {
    echo 'A Python 3.11–3.13 environment is required to build the wheel.' >&2
    exit 1
}

mkdir -p dist/wheels
build_options=()
if "$python_bin" -c 'from importlib.metadata import version; assert int(version("setuptools").split(".")[0]) >= 80; version("wheel")' >/dev/null 2>&1; then
    build_options=(--no-build-isolation)
fi
"$python_bin" -m pip wheel --no-deps "${build_options[@]}" --wheel-dir dist/wheels .
"$python_bin" scripts/wheel_path.py
