#!/usr/bin/env bash
# 停止 SQL-first 整栈：cover → C → B → core（DB/app/view）。
# core 只有在 huellax.state 记录 core_owned=1（即确实由集成启动器启动）时才停；
# 手工用 start_all.sh 起的 core 会保留并提示。只停 PID 文件校验通过的本启动器进程。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=huellax_lib.sh
source "$SCRIPT_DIR/huellax_lib.sh"

hx_parse_args "$(basename "$0")" "$@"
launcher_require_commands || exit 1
hx_check_state_ports || exit 1

echo "HuellaX integrated stop (profile=$PROFILE)"
echo "  core ports : app=$APP_PORT db=$DB_PORT view=$VIEW_PORT"
echo "  extra ports: B=$CATALOG_PORT C=$ANYFIELD_PORT cover=$COVER_PORT"

# 启动进行中不允许 stop，避免 race。
if [ -f "$HX_LOCK/pid" ]; then
  lock_pid="$(tr -cd '0-9' <"$HX_LOCK/pid")"
  if [ -n "$lock_pid" ] && pid_alive "$lock_pid"; then
    echo "Error: start_huellax.sh is still running (pid=$lock_pid); stop after it finishes." >&2
    exit 1
  fi
fi
if [ -f "$RUN_DIR/.lock/pid" ]; then
  lock_pid="$(tr -cd '0-9' <"$RUN_DIR/.lock/pid")"
  if [ -n "$lock_pid" ] && pid_alive "$lock_pid"; then
    echo "Error: start_all.sh is still running (pid=$lock_pid); stop after it finishes." >&2
    exit 1
  fi
fi

core_owned="$(hx_state_get core_owned 2>/dev/null || true)"
[ -n "$core_owned" ] || core_owned=0

rc=0
echo
echo "Stopping integrated extras (reverse start order)..."
for svc in cover anyfield catalog; do
  if [ -f "$(pidfile "$svc")" ]; then
    stop_one "$svc" || rc=1
  else
    echo "  $svc: not started by the integrated launcher (no PID file)"
  fi
done

echo
echo "Stopping core (DB/app/view)..."
if [ "$core_owned" -eq 1 ]; then
  "$SCRIPT_DIR/stop_all.sh" $(hx_core_flags) || rc=1
else
  core_listening=0
  for svc in db app view; do
    if port_has_listener "$(service_port "$svc")"; then
      core_listening=1
    fi
  done
  if [ "$core_listening" -eq 1 ]; then
    echo "  core services are running but were not started by this integrated run; left untouched."
    echo "  To stop them explicitly: ./stop_all.sh $(hx_core_flags)"
  else
    echo "  core services are not running (or not owned by the launcher)"
  fi
fi

if [ "$rc" -eq 0 ]; then
  rm -f "$HX_STATE" 2>/dev/null || true
fi

# 进程退出后端口通常立即释放；最多等 3 s，避免把瞬间的 LISTEN 误报成残留。
for ((i = 0; i < 30; i++)); do
  any_listen=0
  for svc in app db view catalog anyfield cover; do
    if port_has_listener "$(service_port "$svc")"; then any_listen=1; fi
  done
  if [ "$any_listen" -eq 0 ]; then break; fi
  sleep 0.1
done

echo
echo "Port check (foreign listeners are reported, never killed):"
for svc in app db view catalog anyfield cover; do
  port="$(service_port "$svc")"
  if port_has_listener "$port"; then
    if [ "$core_owned" -eq 0 ]; then
      case "$svc" in
        app|db|view)
          if hx_pid_owned "$svc"; then
            echo "  left $(service_label "$svc") port $port running: launcher-owned core, core_owned=0"
            echo "      explicit stop: ./stop_all.sh $(hx_core_flags)"
            continue
          fi
          ;;
      esac
    fi
    echo "  ! $(service_label "$svc") port $port still has a listener:"
    while IFS= read -r line; do
      [ -n "$line" ] && echo "      $line"
    done < <(port_owner_lines "$port")
  else
    echo "  ok $(service_label "$svc") port $port released"
  fi
done

if [ "$rc" -eq 0 ]; then
  echo
  echo "Integrated stop complete."
else
  echo
  echo "Integrated stop did not fully succeed; see PID/command lines above. State file kept for retry." >&2
fi
exit "$rc"
