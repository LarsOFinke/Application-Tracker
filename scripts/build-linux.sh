#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
[[ "$(uname -s)" == Linux ]] || { echo 'AppImage builds require Linux' >&2; exit 1; }

supported_python() {
    "$1" -c 'import sys; sys.exit(not ((3, 11) <= sys.version_info[:2] < (3, 14)))' \
        >/dev/null 2>&1
}

mkdir -p build/logs
run_logged() {
    local name="$1"
    shift
    local log="$PWD/build/logs/$name.log"
    echo "Running $name (details: $log)"
    if "$@" >"$log" 2>&1; then
        tail -n 8 "$log"
    else
        echo "$name failed; last 80 log lines:" >&2
        tail -n 80 "$log" >&2
        return 1
    fi
}

case "$(uname -m)" in
    x86_64) arch=x86_64; sha=ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0 ;;
    aarch64) arch=aarch64; sha=f0837e7448a0c1e4e650a93bb3e85802546e60654ef287576f46c71c126a9158 ;;
    *) echo 'AppImage builds support x86_64 and aarch64 only' >&2; exit 1 ;;
esac

if [[ -n "${BUILD_PYTHON:-}" ]]; then
    build_python="$BUILD_PYTHON"
    supported_python "$build_python" || {
        echo 'BUILD_PYTHON must use Python 3.11–3.13.' >&2
        exit 1
    }
else
    build_python="$PWD/.build-venv/bin/python"
    if [[ ! -x "$build_python" ]] || ! supported_python "$build_python"; then
        python_bin="${PYTHON_BIN:-}"
        if [[ -z "$python_bin" ]]; then
            for candidate in "$PWD/.venv/bin/python" python3.13 python3.12 python3.11 \
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
        if [[ -e .build-venv ]]; then
            [[ -f .build-venv/pyvenv.cfg ]] || { echo '.build-venv exists but is not a virtual environment' >&2; exit 1; }
            rm -rf .build-venv
        fi
        "$python_bin" -m venv .build-venv
        echo "Created .build-venv with $($build_python -V)"
    fi
fi

run_logged wheel env PYTHON_BIN="$build_python" bash scripts/build-wheel.sh
wheel="$($build_python scripts/wheel_path.py)"
run_logged install "$build_python" -m pip install --upgrade "$wheel" 'pyinstaller==6.22.3'
run_logged reinstall-wheel "$build_python" -m pip install --force-reinstall --no-deps "$wheel"
"$build_python" -c 'import PyInstaller, kivy, sqlalchemy, application_tracker' >/dev/null

mkdir -p build dist/linux
run_logged pyinstaller "$build_python" -m PyInstaller --log-level=WARN \
    --clean --noconfirm --onefile --windowed \
    --name ApplicationTracker \
    --collect-submodules sqlalchemy.dialects.sqlite \
    --distpath dist/linux --workpath build/pyinstaller --specpath build \
    scripts/frozen_entry.py

tool="${APPIMAGETOOL:-$PWD/build/tools/appimagetool-$arch.AppImage}"
if [[ -z "${APPIMAGETOOL:-}" && ! -f "$tool" ]]; then
    mkdir -p build/tools
    curl --fail --location --retry 3 --silent --show-error \
        "https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-$arch.AppImage" \
        --output "$tool.partial"
    printf '%s  %s\n' "$sha" "$tool.partial" | sha256sum --check --status
    mv "$tool.partial" "$tool"
fi
[[ -f "$tool" ]] || { echo "appimagetool not found: $tool" >&2; exit 1; }
if [[ -z "${APPIMAGETOOL:-}" ]]; then
    chmod +x "$tool"
fi

appdir="$PWD/build/ApplicationTracker.AppDir"
rm -rf "$appdir"
mkdir -p "$appdir/usr/bin"
cp dist/linux/ApplicationTracker "$appdir/usr/bin/ApplicationTracker"
cp packaging/linux/ApplicationTracker.desktop "$appdir/ApplicationTracker.desktop"
cp packaging/linux/ApplicationTracker.svg "$appdir/ApplicationTracker.svg"
cp packaging/linux/AppRun "$appdir/AppRun"
chmod +x "$appdir/AppRun"

output="$PWD/dist/linux/ApplicationTracker-$arch.AppImage"
rm -f "$output"
runtime_args=()
if [[ -n "${APPIMAGE_RUNTIME:-}" ]]; then
    [[ -f "$APPIMAGE_RUNTIME" ]] || { echo "AppImage runtime not found: $APPIMAGE_RUNTIME" >&2; exit 1; }
    runtime_args=(--runtime-file "$APPIMAGE_RUNTIME")
else
    runtime="$PWD/build/tools/runtime-$arch"
    mkdir -p "$(dirname "$runtime")"
    offset="$(APPIMAGE_EXTRACT_AND_RUN=1 "$tool" --appimage-offset)"
    [[ "$offset" =~ ^[0-9]+$ && "$offset" -gt 0 ]] || {
        echo "Could not read the embedded AppImage runtime from $tool" >&2
        exit 1
    }
    head -c "$offset" "$tool" > "$runtime"
    runtime_args=(--runtime-file "$runtime")
fi
run_logged appimagetool env ARCH="$arch" APPIMAGE_EXTRACT_AND_RUN=1 "$tool" --no-appstream \
    "${runtime_args[@]}" "$appdir" "$output"
chmod +x "$output"
mkdir -p build/smoke-data
XDG_DATA_HOME="$PWD/build/smoke-data" KIVY_NO_FILELOG=1 \
    APPIMAGE_EXTRACT_AND_RUN=1 "$output" --version
XDG_DATA_HOME="$PWD/build/smoke-data" KIVY_NO_FILELOG=1 KIVY_WINDOW=mock \
    APPIMAGE_EXTRACT_AND_RUN=1 "$output" --check-imports
echo "Built $output"
