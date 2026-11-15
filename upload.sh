#!/usr/bin/env bash
# =============================================================================
# horizon_mod_builder / upload.sh
#
# Pack mods from your computer, upload them as a temporary GitHub release
# asset, and start the "Build Horizon Mod" workflow. The workflow builds all
# mods into one importable package by default.
#
# Examples:
#   ./upload.sh                                  # HORIZON_MODS_DIR, ~/horizon-mods, or .
#   ./upload.sh ~/Downloads/my-mod.hnmod
#   ./upload.sh ~/my-mods mod_menu.hnmod
#   ./upload.sh --profile performance --watch ~/my-mods
#   ./upload.sh --separate ~/my-mods             # one archive per mod
#   ./upload.sh --dry-run ~/my-mods              # package only, print commands
#
# Requires: bash, python3, git and the GitHub CLI (gh), logged in with
# `gh auth login`. Run it from this repository clone or pass --repo.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO=""
HORIZON_VERSION="${HORIZON_VERSION:-latest}"
PROFILE="${NATIVE_PROFILE:-performance}"
MODE="combined"
WATCH=0
CLEANUP=0
DRY_RUN=0
PATHS=()

usage() {
  sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="${2:-}"
      [[ -n "$REPO" ]] || { echo "error: --repo needs OWNER/REPO" >&2; exit 2; }
      shift 2
      ;;
    --horizon-version)
      HORIZON_VERSION="${2:-}"
      [[ -n "$HORIZON_VERSION" ]] || { echo "error: --horizon-version needs a tag" >&2; exit 2; }
      shift 2
      ;;
    --profile)
      PROFILE="${2:-}"
      [[ "$PROFILE" =~ ^(performance|dev|release)$ ]] || {
        echo "error: --profile must be performance, dev or release" >&2; exit 2;
      }
      shift 2
      ;;
    --mode)
      MODE="${2:-}"
      [[ "$MODE" =~ ^(combined|separate)$ ]] || {
        echo "error: --mode must be combined or separate" >&2; exit 2;
      }
      shift 2
      ;;
    --separate)
      MODE="separate"
      shift
      ;;
    --combined|--combine)
      MODE="combined"
      shift
      ;;
    --watch)
      WATCH=1
      shift
      ;;
    --cleanup)
      CLEANUP=1
      shift
      ;;
    --keep-upload)
      CLEANUP=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      PATHS+=("$@")
      break
      ;;
    -*)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      PATHS+=("$1")
      shift
      ;;
  esac
done

command -v python3 >/dev/null 2>&1 || {
  echo "error: python3 is required" >&2
  exit 1
}
command -v gh >/dev/null 2>&1 || {
  echo "error: the GitHub CLI (gh) is required: https://cli.github.com" >&2
  exit 1
}
command -v git >/dev/null 2>&1 || {
  echo "error: git is required" >&2
  exit 1
}

if [[ ${#PATHS[@]} -eq 0 ]]; then
  if [[ -n "${HORIZON_MODS_DIR:-}" ]]; then
    PATHS=("$HORIZON_MODS_DIR")
  elif [[ -d "$HOME/horizon-mods" ]]; then
    PATHS=("$HOME/horizon-mods")
  else
    PATHS=(".")
  fi
fi

if [[ -z "$REPO" ]]; then
  REPO="$(git -C "$SCRIPT_DIR" config --get remote.origin.url 2>/dev/null || true)"
  if [[ "$REPO" =~ github\.com[:/]([^/]+/[^/.]+)(\.git)?$ ]]; then
    REPO="${BASH_REMATCH[1]}"
  else
    REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
  fi
fi
if [[ -z "$REPO" ]]; then
  echo "error: could not detect the GitHub repository; pass --repo OWNER/REPO" >&2
  exit 1
fi

gh auth status >/dev/null 2>&1 || {
  echo "error: gh is not logged in. Run: gh auth login" >&2
  exit 1
}

STAMP="$(date -u +%Y%m%d-%H%M%S)"
TAG="mod-upload-$STAMP"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/horizon-upload.XXXXXX")"
cleanup_tmp() {
  rm -rf "$TMP_DIR"
}
trap cleanup_tmp EXIT

if [[ "$DRY_RUN" == "1" ]]; then
  ZIP_PATH="$PWD/horizon-mods-$STAMP.zip"
else
  ZIP_PATH="$TMP_DIR/horizon-mods-$STAMP.zip"
fi

echo "Packing local mods from:"
for path in "${PATHS[@]}"; do
  echo "  - $path"
done
python3 "$SCRIPT_DIR/scripts/pack_mods_zip.py" --output "$ZIP_PATH" "${PATHS[@]}"

ASSET_NAME="$(basename "$ZIP_PATH")"
ASSET_URL="https://github.com/$REPO/releases/download/$TAG/$ASSET_NAME"
NOTES="Temporary upload for the Horizon mod builder. Safe to delete after the workflow finishes."

if [[ "$DRY_RUN" == "1" ]]; then
  cat <<EOF

Dry run: packaged $ZIP_PATH
Would create release:
  gh release create "$TAG" "$ZIP_PATH" --repo "$REPO" --title "Horizon mod upload $STAMP" --notes "$NOTES" --prerelease
Would start workflow:
  gh workflow run build.yml --repo "$REPO" \\
    -f mod_source="$ASSET_URL" \\
    -f horizon_version="$HORIZON_VERSION" \\
    -f native_profile="$PROFILE" \\
    -f mode="$MODE"
EOF
  exit 0
fi

echo
echo "Uploading mod package as release asset..."
gh release create "$TAG" "$ZIP_PATH" \
  --repo "$REPO" \
  --title "Horizon mod upload $STAMP" \
  --notes "$NOTES" \
  --prerelease

PREV_RUN_ID="$(gh run list --repo "$REPO" --workflow build.yml \
  --event workflow_dispatch --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || true)"
echo "Starting the build workflow..."
gh workflow run build.yml \
  --repo "$REPO" \
  -f "mod_source=$ASSET_URL" \
  -f "horizon_version=$HORIZON_VERSION" \
  -f "native_profile=$PROFILE" \
  -f "mode=$MODE"

RUN_ID=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  sleep 2
  RUN_ID="$(gh run list --repo "$REPO" --workflow build.yml \
    --event workflow_dispatch --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || true)"
  if [[ -n "$RUN_ID" && "$RUN_ID" != "$PREV_RUN_ID" ]]; then
    break
  fi
  RUN_ID=""
done

echo
if [[ -n "$RUN_ID" ]]; then
  echo "Workflow: https://github.com/$REPO/actions/runs/$RUN_ID"
else
  echo "Workflow started. Open: https://github.com/$REPO/actions/workflows/build.yml"
fi
echo "Download the artifact named horizon-mod-build-<run-number> after the run finishes."

if [[ "$WATCH" == "1" && -n "$RUN_ID" ]]; then
  echo
  echo "Watching the workflow (this can take 20-30 minutes)..."
  if gh run watch "$RUN_ID" --repo "$REPO" --exit-status; then
    RESULT=0
  else
    RESULT=$?
    echo "The workflow did not finish successfully (exit $RESULT)." >&2
  fi
  if [[ "$CLEANUP" == "1" ]]; then
    echo "Deleting the temporary upload release $TAG..."
    gh release delete "$TAG" --repo "$REPO" --cleanup-tag --yes || true
  else
    echo "Temporary upload kept. Delete it with:"
    echo "  gh release delete $TAG --repo $REPO --cleanup-tag --yes"
  fi
  exit "$RESULT"
fi

echo "Temporary upload kept for the workflow. Delete it later with:"
echo "  gh release delete $TAG --repo $REPO --cleanup-tag --yes"
