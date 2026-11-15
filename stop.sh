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
  args=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --app-port|--db-port|--view-port) args+=("$1" "$2"); shift ;;
      --app-port=*|--db-port=*|--view-port=*) args+=("$1") ;;
      --catalog-port|--anyfield-port|--cover-port) shift ;;
      --catalog-port=*|--anyfield-port=*|--cover-port=*) ;;
      *) args+=("$1") ;;
    esac
    shift
  done
  if [ "${#args[@]}" -eq 0 ]; then
    exec bash "$FALLBACK"
  fi
  exec bash "$FALLBACK" "${args[@]}"
fi
echo "No supported stop script found under system/." >&2
exit 1
