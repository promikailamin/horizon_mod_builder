#!/usr/bin/env bash
# Import a built package with the official launcher and smoke-test the binary.
#
# Usage: .agent-work/tests/test_import_built.sh path/to/build.zip [launcher-home]
#
# The launcher home must already have the package's base Horizon version
# installed and prepared (the builder's .work/launcher normally does).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ZIP="${1:?usage: $0 path/to/build.zip [launcher-home]}"
HOME_DIR="${2:-${HORIZON_LAUNCHER_HOME:-$ROOT/.work/launcher}}"

export HORIZON_LAUNCHER_HOME="$HOME_DIR"
export HORIZON_HOME="${HORIZON_HOME:-$ROOT/.work/game}"
export HORIZON_NO_AUDIO=1
export HORIZON_LAUNCHER_NO_SELF_UPDATE=1
export HORIZON_LAUNCHER_TRASH="$HOME_DIR/trash"
export HORIZON_LAUNCHER_CLIPBOARD="$HOME_DIR/clipboard"
export HORIZON_LAUNCHER_DESKTOP="$HOME_DIR/desktop"

"$ROOT/horizon_launcher" import-build "$ZIP" --trust-unsigned
LATEST="$(ls -dt "$HOME_DIR"/versions/imported-* | head -1)"
"$LATEST/horizon-client" --help >/dev/null
echo "Imported and smoke-tested: $LATEST"
