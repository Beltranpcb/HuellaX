#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYS="$ROOT/system"
if [ ! -d "$SYS" ]; then
  echo "Missing system/ submodule. Run: git submodule update --init --recursive" >&2
  exit 1
fi
LAUNCHER="$(find "$SYS" -type f -name 'start_huellax.sh' -print -quit 2>/dev/null || true)"
if [ -n "$LAUNCHER" ]; then
  exec bash "$LAUNCHER" "$@"
fi
FALLBACK="$(find "$SYS" -type f -name 'start_all.sh' -print -quit 2>/dev/null || true)"
if [ -n "$FALLBACK" ]; then
  exec bash "$FALLBACK" "$@"
fi
echo "No supported launcher found under system/." >&2
exit 1
