#!/usr/bin/env bash
# =============================================================================
# horizon_mod_builder / build.sh
# Builds Horizon native mods using the Horizon Launcher.
#
# Usage:
#   ./build.sh [mod-name-or-repo]
#
# If an argument is given it is treated as the mod source (a local folder or a
# git repo URL) to build. Otherwise the default horizon-prepare crate is used.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$SCRIPT_DIR/horizon_launcher"
MOD_SRC="${1:-}"

echo "=== Horizon Mod Builder ==="
echo "Working dir: $SCRIPT_DIR"

# Make sure launcher is executable
chmod +x "$LAUNCHER"

# Install native build dependencies (needed on fresh Linux runners)
if command -v apt-get >/dev/null 2>&1; then
  echo "Installing native build dependencies..."
  sudo apt-get update -y
  sudo apt-get install -y build-essential pkg-config libasound2-dev libudev-dev
fi

# If a mod source was provided, copy it into the mods/ working folder
if [[ -n "$MOD_SRC" ]]; then
  echo "Preparing mod source: $MOD_SRC"
  rm -rf "$SCRIPT_DIR/mods/work"
  mkdir -p "$SCRIPT_DIR/mods/work"
  if [[ "$MOD_SRC" == http* ]]; then
    git clone --depth 1 "$MOD_SRC" "$SCRIPT_DIR/mods/work"
  else
    cp -r "$MOD_SRC"/* "$SCRIPT_DIR/mods/work/"
  fi
fi

# Run the native build
echo "Running horizon_launcher native-build..."
"$LAUNCHER" native-build --trust-native-code

echo "=== Build complete ==="
