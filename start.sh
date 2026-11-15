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
  # The core launcher accepts only app/db/view. B/C/cover remain optional
  # services in the primary submodule; see the runbook there.
  args=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --app-port|--db-port|--view-port|--offline)
        args+=("$1"); [ "$1" = "--offline" ] || { args+=("$2"); shift; } ;;
      --app-port=*|--db-port=*|--view-port=*) args+=("$1") ;;
      --catalog-port|--anyfield-port|--cover-port) shift ;;
      --catalog-port=*|--anyfield-port=*|--cover-port=*) ;;
      *) args+=("$1") ;;
    esac
    shift
  done
  exec bash "$FALLBACK" "${args[@]}"
fi
echo "No supported launcher found under system/." >&2
exit 1
