#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYS="$ROOT/system"
if [ ! -d "$SYS" ]; then
  echo "Missing system/ submodule." >&2
  exit 1
fi
STOPPER="$(find "$SYS" -type f -name 'stop_huellax.sh' -print -quit 2>/dev/null || true)"
if [ -n "$STOPPER" ]; then
  exec bash "$STOPPER" "$@"
fi
FALLBACK="$(find "$SYS" -type f -name 'stop_all.sh' -print -quit 2>/dev/null || true)"
if [ -n "$FALLBACK" ]; then
  exec bash "$FALLBACK" "$@"
fi
echo "No supported stop script found under system/." >&2
exit 1
