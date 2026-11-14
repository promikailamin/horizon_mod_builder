#!/usr/bin/env bash
# =============================================================================
# horizon_mod_builder / build.sh
#
# Compile Horizon native mods and collect downloadable artifacts.
#
# Usage:
#   ./build.sh                         # build the test mods from issue #1
#   ./build.sh /path/to/mod            # build a bundle, folder, or .hnmod
#   ./build.sh https://github.com/u/r  # build a GitHub source/release
#   ./build.sh --issue-body "$TEXT"    # extract mod URLs from issue text
#
# Every argument is passed to scripts/build_mods.py.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "${HORIZON_BUILDER_SKIP_DEPS:-0}" != "1" ]] && command -v apt-get >/dev/null 2>&1; then
  missing=0
  for package in build-essential pkg-config libasound2-dev libudev-dev \
                 libxkbcommon-x11-0 libxkbcommon0 libxcb-xkb1; do
    if ! dpkg -s "$package" >/dev/null 2>&1; then
      missing=1
      break
    fi
  done
  if [[ "$missing" == "1" ]]; then
    echo "Installing native build and launcher dependencies..."
    sudo apt-get update -y
    sudo apt-get install -y \
      build-essential pkg-config libasound2-dev libudev-dev \
      libxkbcommon-x11-0 libxkbcommon0 libxcb-xkb1 libxcb1 libx11-xcb1
  fi
fi

exec python3 "$SCRIPT_DIR/scripts/build_mods.py" "$@"
