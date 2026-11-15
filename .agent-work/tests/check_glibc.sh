#!/usr/bin/env bash
# Check the highest GLIBC symbol version required by a Horizon build.
#
# Usage:
#   .agent-work/tests/check_glibc.sh path/to/build.zip [max-version]
#   .agent-work/tests/check_glibc.sh path/to/horizon-client [max-version]
#
# The default maximum is 2.35, the baseline used by the official Horizon
# Linux binaries and by docker/portable-builder.Dockerfile.
set -euo pipefail

TARGET="${1:?usage: $0 ZIP_OR_BINARY [max-version]}"
MAX="${2:-2.35}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [[ -f "$TARGET" && "$TARGET" == *.zip ]]; then
  unzip -q "$TARGET" -d "$TMP"
  ROOT="$TMP"
elif [[ -d "$TARGET" ]]; then
  ROOT="$TARGET"
else
  ROOT="$(dirname "$TARGET")"
  mkdir -p "$TMP"
  cp "$TARGET" "$TMP/"
  ROOT="$TMP"
fi

status=0
found=0
while IFS= read -r -d '' file; do
  if ! file -b "$file" | grep -q 'ELF'; then
    continue
  fi
  highest="$(objdump -T "$file" 2>/dev/null \
    | grep -o 'GLIBC_[0-9][0-9.]*' \
    | sed 's/^GLIBC_//' \
    | sort -V \
    | tail -1 || true)"
  [[ -n "$highest" ]] || continue
  found=1
  printf '%-24s max GLIBC %s\n' "$(basename "$file")" "$highest"
  if [[ "$(printf '%s\n%s\n' "$highest" "$MAX" | sort -V | tail -1)" != "$MAX" ]]; then
    printf 'error: %s needs GLIBC %s but the limit is %s\n' "$file" "$highest" "$MAX" >&2
    status=1
  fi
done < <(find "$ROOT" -maxdepth 2 -type f \( -name 'horizon-*' -o -name '*.so*' \) -print0)

if [[ "$found" == "0" ]]; then
  echo "error: no ELF binaries found in $TARGET" >&2
  exit 2
fi
if [[ "$status" == "0" ]]; then
  echo "OK: every binary requires at most GLIBC $MAX"
fi
exit "$status"
