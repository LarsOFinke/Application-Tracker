#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
[[ "$(uname -s)" == Linux ]] || { echo 'AppImage builds require Linux' >&2; exit 1; }

case "$(uname -m)" in
    x86_64) arch=x86_64; sha=ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0 ;;
    aarch64) arch=aarch64; sha=f0837e7448a0c1e4e650a93bb3e85802546e60654ef287576f46c71c126a9158 ;;
    *) echo 'AppImage builds support x86_64 and aarch64 only' >&2; exit 1 ;;
esac

if [[ -n "${BUILD_PYTHON:-}" ]]; then
    build_python="$BUILD_PYTHON"
else
    build_python="$PWD/.build-venv/bin/python"
    if [[ ! -x "$build_python" ]]; then
        python_bin="${PYTHON_BIN:-python3}"
        "$python_bin" -m venv .build-venv
    fi
    "$build_python" -m pip install -e . 'pyinstaller==6.22.3'
fi
"$build_python" -c 'import PyInstaller, kivy, sqlalchemy' >/dev/null

mkdir -p build dist/linux
"$build_python" -m PyInstaller --noconfirm --onefile --windowed \
    --name ApplicationTracker --paths "$PWD/src" \
    --collect-submodules sqlalchemy.dialects.sqlite \
    --distpath dist/linux --workpath build/pyinstaller --specpath build \
    scripts/frozen_entry.py

tool="${APPIMAGETOOL:-$PWD/build/tools/appimagetool-$arch.AppImage}"
if [[ -z "${APPIMAGETOOL:-}" && ! -f "$tool" ]]; then
    mkdir -p build/tools
    curl --fail --location --retry 3 \
        "https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-$arch.AppImage" \
        --output "$tool.partial"
    printf '%s  %s\n' "$sha" "$tool.partial" | sha256sum --check --status
    mv "$tool.partial" "$tool"
fi
[[ -f "$tool" ]] || { echo "appimagetool not found: $tool" >&2; exit 1; }

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
fi
ARCH="$arch" APPIMAGE_EXTRACT_AND_RUN=1 "$tool" --no-appstream \
    "${runtime_args[@]}" "$appdir" "$output"
chmod +x "$output"
mkdir -p build/smoke-data
XDG_DATA_HOME="$PWD/build/smoke-data" KIVY_NO_FILELOG=1 \
    APPIMAGE_EXTRACT_AND_RUN=1 "$output" --version
XDG_DATA_HOME="$PWD/build/smoke-data" KIVY_NO_FILELOG=1 KIVY_WINDOW=mock \
    APPIMAGE_EXTRACT_AND_RUN=1 "$output" --check-imports
echo "Built $output"
