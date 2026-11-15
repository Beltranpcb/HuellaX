#!/usr/bin/env bash
# 只读状态：整栈六端口 health、PID 归属、SQL 数据源、封面根、集成状态文件。
# 退出码 0 = 当前可用/已启用服务均健康；1 = 有服务不健康或状态文件端口不一致。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=huellax_lib.sh
source "$SCRIPT_DIR/huellax_lib.sh"

hx_parse_args "$(basename "$0")" "$@"
launcher_require_commands || exit 1
hx_resolve_stack || exit 1

state_ok=1
hx_check_state_ports || state_ok=0

echo "HuellaX integrated status (profile=$PROFILE)"
echo "  time: $(iso_now)"
echo "  workspace: $LAUNCHER_ROOT_DIR"
echo "  git: $(launcher_git_rev)"
hx_print_header
echo
if [ -f "$HX_STATE" ]; then
  echo "Integrated state: ${HX_STATE#"$LAUNCHER_ROOT_DIR"/}"
  echo "  started_at : $(hx_state_get started_at 2>/dev/null || echo "?")"
  echo "  core_owned : $(hx_state_get core_owned 2>/dev/null || echo "?")  (1 = stop_huellax may stop core)"
  if [ "$state_ok" -eq 0 ]; then
    echo "  warning    : state file ports differ from the requested ports (see error above)"
  fi
else
  echo "Integrated state: none (core may have been started manually with start_all.sh)"
fi
if [ -f "$HX_LOCK/pid" ]; then
  lock_pid="$(tr -cd '0-9' <"$HX_LOCK/pid")"
  if [ -n "$lock_pid" ] && pid_alive "$lock_pid"; then
    echo "Start lock: held by pid=$lock_pid"
  else
    echo "Start lock: stale (pid=${lock_pid:-?} is gone)"
  fi
fi

hx_health_report
hx_data_report
hx_print_hints

echo
if hx_required_check; then
  echo "Conclusion: required services healthy (B and cover only when available/enabled)."
  [ "$state_ok" -eq 1 ] || exit 1
  exit 0
fi
echo "Conclusion: one or more required services are unhealthy." >&2
exit 1
